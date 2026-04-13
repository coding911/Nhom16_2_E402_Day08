from typing import List, Dict
import json
import numpy as np
import faiss

from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from groq import Groq
import re


# =========================
# CONFIG
# =========================
MODEL_NAME = "all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
GROQ_MODEL = "qwen/qwen3-32b"

model = SentenceTransformer(MODEL_NAME)
reranker = CrossEncoder(RERANK_MODEL)
client = Groq(api_key="YOUR_API_KEY")


# =========================
# LOAD DATA
# =========================
def load_chunks(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_index(path: str):
    return faiss.read_index(path)


# =========================
# BM25
# =========================
def build_bm25(chunks):
    corpus = [c["text"].split() for c in chunks]
    bm25 = BM25Okapi(corpus)
    return bm25, corpus


# =========================
# DENSE SEARCH
# =========================
def dense_search(query, index, chunks, top_k=5):
    q = model.encode([query]).astype("float32")
    faiss.normalize_L2(q)

    D, I = index.search(q, top_k)

    return [chunks[i] for i in I[0] if i != -1]


# =========================
# HYBRID SEARCH
# =========================
def hybrid_search(query, index, bm25, corpus, chunks, top_k=5, alpha=0.5):
    q = model.encode([query]).astype("float32")
    faiss.normalize_L2(q)

    D, I = index.search(q, top_k * 2)

    dense_scores = {
        i: float(D[0][idx])
        for idx, i in enumerate(I[0]) if i != -1
    }

    bm25_scores = bm25.get_scores(query.split())

    combined = {}
    for i in range(len(chunks)):
        d = dense_scores.get(i, 0)
        b = bm25_scores[i]
        combined[i] = alpha * d + (1 - alpha) * b

    top_idx = sorted(combined, key=combined.get, reverse=True)[:top_k]

    return [chunks[i] for i in top_idx]


# =========================
# RERANK
# =========================
def rerank(query, candidates, top_k=5):
    pairs = [(query, c["text"]) for c in candidates]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:top_k]]


# =========================
# GENERATE ANSWER (GROQ + CITATION)
# =========================
def generate_answer(query, contexts):
    # limit context
    contexts = contexts[:5]

    # build context block
    context_blocks = []
    for i, c in enumerate(contexts):
        meta = c["metadata"]

        context_blocks.append(
            f"[{i+1}] Section: {meta.get('section','')} | Source: {meta.get('source','')}\n"
            f"{c['text']}"
        )

    context_text = "\n\n".join(context_blocks)

    # 🔥 SYSTEM PROMPT (RẤT QUAN TRỌNG)
    system_prompt = """
Bạn là trợ lý AI nội bộ chuyên trả lời dựa trên tài liệu.

QUY TẮC NGHIÊM NGẶT:
1. Chỉ sử dụng thông tin trong Context.
2. Không được suy diễn, không được thêm kiến thức bên ngoài.
3. Nếu không tìm thấy thông tin → trả lời đúng câu:
   "Không tìm thấy trong tài liệu".
4. BẮT BUỘC phải có citation dạng [1], [2] tương ứng với Context.
5. Không được tạo citation không tồn tại.
6. Không được nhắc lại Context trong câu trả lời.
7. Trả lời ngắn gọn, trực tiếp, đúng trọng tâm.
8. Nếu có nhiều thông tin → tổng hợp lại nhưng vẫn phải giữ citation.

FORMAT TRẢ LỜI:
- Viết thành đoạn văn ngắn
- Citation đặt ngay sau thông tin (VD: ... 4 giờ [1])
"""

    # 🔥 USER PROMPT (clean, chỉ data)
    user_prompt = f"""
Context:
{context_text}

Question:
{query}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0,
        max_tokens=512
    )

    answer = response.choices[0].message.content.strip()
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
    # build citation map
    citations = []
    for i, c in enumerate(contexts):
        meta = c["metadata"]
        citations.append({
            "id": i + 1,
            "section": meta.get("section"),
            "source": meta.get("source"),
            "file": meta.get("file_name")
        })

    return {
        "answer": answer,
        "citations": citations
    }

# =========================
# MASTER PIPELINE
# =========================
def retrieve_and_answer(
    query,
    index,
    chunks,
    bm25=None,
    corpus=None,
    use_hybrid=True,
    use_rerank=True,
    top_k=5
):
    # Retrieval
    if use_hybrid and bm25:
        candidates = hybrid_search(query, index, bm25, corpus, chunks, top_k * 2)
    else:
        candidates = dense_search(query, index, chunks, top_k * 2)

    # Rerank
    if use_rerank:
        candidates = rerank(query, candidates, top_k)
    else:
        candidates = candidates[:top_k]

    # Answer
    return generate_answer(query, candidates)


# =========================
# MAIN
# =========================
def main():
    print("🚀 Loading system...")

    chunks = load_chunks("chunks_meta.json")
    index = load_index("faiss.index")

    bm25, corpus = build_bm25(chunks)

    print("✅ Ready")

    while True:
        query = input("\n🔍 Nhập câu hỏi (hoặc 'exit'): ").strip()

        if query.lower() in ["exit", "quit"]:
            print("👋 Bye!")
            break

        if not query:
            print("⚠️ Query rỗng, nhập lại.")
            continue

        result = retrieve_and_answer(
            query=query,
            index=index,
            chunks=chunks,
            bm25=bm25,
            corpus=corpus,
            use_hybrid=True,
            use_rerank=True
        )

        print("\n📌 ANSWER:")
        print(result["answer"])

        print("\n📚 CITATIONS:")
        for c in result["citations"]:
            print(f"[{c['id']}] {c['section']} ({c['source']})")