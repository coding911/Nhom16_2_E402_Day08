import json
from datetime import datetime

from rag_answer import (
    retrieve_and_answer,
    load_chunks,
    load_index,
    build_bm25
)

# =========================
# CONFIG
# =========================
INPUT_FILE = "grading_questions.json"
OUTPUT_FILE = "grading_results.json"

USE_HYBRID = True
USE_RERANK = True
RETRIEVAL_MODE = "hybrid"


# =========================
# LOAD DATA
# =========================
def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# MAIN PIPELINE
# =========================
def main():
    print("🚀 Loading system...")

    chunks = load_chunks("chunks_meta.json")
    index = load_index("faiss.index")
    bm25, corpus = build_bm25(chunks)

    questions = load_questions(INPUT_FILE)

    print(f"✅ Loaded {len(questions)} questions")

    results = []

    for q in questions:
        print(f"\n🔍 {q['id']} - {q['question']}")

        result = retrieve_and_answer(
            query=q["question"],
            index=index,
            chunks=chunks,
            bm25=bm25,
            corpus=corpus,
            use_hybrid=USE_HYBRID,
            use_rerank=USE_RERANK
        )

        answer = result["answer"]

        # extract sources
        sources = list(set([
            c.get("source") for c in result["citations"] if c.get("source")
        ]))

        # build output record
        record = {
            "id": q["id"],
            "question": q["question"],
            "answer": answer,
            "sources": sources,
            "chunks_retrieved": len(result["citations"]),
            "retrieval_mode": RETRIEVAL_MODE,
            "timestamp": datetime.now().isoformat()
        }

        results.append(record)

    # =========================
    # SAVE OUTPUT
    # =========================
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()