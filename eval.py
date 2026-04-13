from typing import List, Dict
import time
import numpy as np
import json
import re

# =========================
# INPUT
# =========================
from rag_answer import (
    retrieve_and_answer,
    load_chunks,
    load_index,
    build_bm25
)

# =========================
# LOAD TEST DATA
# =========================
def extract_keywords(text: str) -> List[str]:
    text = text.lower()

    keywords = []
    patterns = re.findall(r"\d+\s*\w+", text)
    keywords.extend(patterns)

    important_words = [
        "engineer", "manager", "admin", "security",
        "không", "có", "được", "khóa", "remote"
    ]

    for w in important_words:
        if w in text:
            keywords.append(w)

    return list(set(keywords))


def load_test_queries(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = []
    for item in data:
        queries.append({
            "query": item["question"],
            "expected_answer": item["expected_answer"],
            "expected_keywords": extract_keywords(item["expected_answer"])
        })

    return queries


# =========================
# METRICS
# =========================
def keyword_match_score(answer: str, expected_keywords: List[str]) -> float:
    answer = answer.lower()
    hits = sum(1 for k in expected_keywords if k in answer)
    return hits / len(expected_keywords) if expected_keywords else 0.0


def faithfulness_score(answer: str, contexts: List[Dict]) -> float:
    context_text = " ".join([c["text"].lower() for c in contexts])
    answer_words = answer.lower().split()

    if not answer_words:
        return 0.0

    hits = sum(1 for w in answer_words if w in context_text)
    return hits / len(answer_words)


def answer_relevance_score(answer: str, query: str) -> float:
    q_words = set(query.lower().split())
    a_words = set(answer.lower().split())

    if not q_words:
        return 0.0

    return len(q_words & a_words) / len(q_words)


def context_recall_score(contexts: List[Dict], expected_keywords: List[str]) -> float:
    context_text = " ".join([c["text"].lower() for c in contexts])

    if not expected_keywords:
        return 0.0

    hits = sum(1 for k in expected_keywords if k in context_text)
    return hits / len(expected_keywords)


def completeness_score(answer: str, expected_keywords: List[str]) -> float:
    return keyword_match_score(answer, expected_keywords)


# =========================
# EVALUATE
# =========================
def evaluate_variant(
    name,
    queries,
    index,
    chunks,
    bm25,
    corpus,
    use_hybrid,
    use_rerank
):
    results = []

    print(f"\n🚀 Evaluating: {name}")

    for q in queries:
        start = time.time()

        # retrieve + answer
        result = retrieve_and_answer(
            query=q["query"],
            index=index,
            chunks=chunks,
            bm25=bm25,
            corpus=corpus,
            use_hybrid=use_hybrid,
            use_rerank=use_rerank
        )

        latency = time.time() - start

        answer = result["answer"]

        # ⚠️ lấy contexts từ citations (giả định cùng index)
        contexts = []
        for c in result["citations"]:
            idx = c["id"] - 1
            if idx < len(chunks):
                contexts.append(chunks[idx])

        # metrics
        faith = faithfulness_score(answer, contexts)
        rel = answer_relevance_score(answer, q["query"])
        recall = context_recall_score(contexts, q["expected_keywords"])
        comp = completeness_score(answer, q["expected_keywords"])

        results.append({
            "query": q["query"],
            "answer": answer,
            "faithfulness": faith,
            "relevance": rel,
            "context_recall": recall,
            "completeness": comp,
            "latency": latency
        })

        print(f"\nQuery: {q['query']}")
        print(f"Faithfulness: {faith:.2f} | Relevance: {rel:.2f}")
        print(f"Context Recall: {recall:.2f} | Completeness: {comp:.2f}")
        print(f"Latency: {latency:.2f}s")

    # aggregate
    return {
        "name": name,
        "faithfulness": np.mean([r["faithfulness"] for r in results]),
        "relevance": np.mean([r["relevance"] for r in results]),
        "context_recall": np.mean([r["context_recall"] for r in results]),
        "completeness": np.mean([r["completeness"] for r in results]),
        "latency": np.mean([r["latency"] for r in results])
    }


# =========================
# MAIN
# =========================
def main():
    print("🚀 Loading system...")

    chunks = load_chunks("chunks_meta.json")
    index = load_index("faiss.index")
    bm25, corpus = build_bm25(chunks)

    queries = load_test_queries("data/test_questions.json")

    results = []

    results.append(
        evaluate_variant(
            "Dense",
            queries,
            index,
            chunks,
            bm25,
            corpus,
            use_hybrid=False,
            use_rerank=False
        )
    )

    results.append(
        evaluate_variant(
            "Hybrid",
            queries,
            index,
            chunks,
            bm25,
            corpus,
            use_hybrid=True,
            use_rerank=False
        )
    )

    results.append(
        evaluate_variant(
            "Hybrid + Rerank",
            queries,
            index,
            chunks,
            bm25,
            corpus,
            use_hybrid=True,
            use_rerank=True
        )
    )

    # =========================
    # SCORECARD
    # =========================
    print("\n" + "=" * 70)
    print("📊 SCORECARD")
    print("=" * 70)

    for r in results:
        print(f"""
{r['name']}
- Faithfulness: {r['faithfulness']:.2f} / 1
- Answer Relevance: {r['relevance']:.2f} / 1
- Context Recall: {r['context_recall']:.2f} / 1
- Completeness: {r['completeness']:.2f} / 1
- Latency: {r['latency']:.2f}s
""")

    # save
    with open("evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("✅ Saved evaluation_report.json")


if __name__ == "__main__":
    main()