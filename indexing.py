from typing import List, Dict
import json
from pathlib import Path
import re
import numpy as np
import uuid
import faiss
from sentence_transformers import SentenceTransformer


# =========================
# CONFIG
# =========================
MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)


# =========================
# 1. METADATA PARSER
# =========================
def extract_metadata(text: str):
    lines = text.strip().split("\n")

    title = lines[0].strip()
    metadata = {"title": title}

    content_start = 0

    for i, line in enumerate(lines[1:], start=1):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().lower().replace(" ", "_")] = value.strip()
        else:
            content_start = i
            break

    content = "\n".join(lines[content_start:])
    return metadata, content


# =========================
# 2. SPLIT LOGIC
# =========================
def split_sections(text: str):
    pattern = r"===\s*(.*?)\s*==="
    parts = re.split(pattern, text)

    sections = []
    for i in range(1, len(parts), 2):
        sections.append((parts[i].strip(), parts[i + 1].strip()))

    return sections


def split_paragraphs(text: str):
    return [p.strip() for p in text.split("\n\n") if p.strip()]


# =========================
# 3. SEMANTIC CHUNKING
# =========================
def semantic_chunk(paragraph: str, threshold=0.3):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', paragraph) if s.strip()]

    if len(sentences) <= 1:
        return sentences

    embeddings = model.encode(sentences)

    def cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sims = [cosine(embeddings[i], embeddings[i + 1]) for i in range(len(sentences) - 1)]

    avg = sum(sims) / len(sims)
    breakpoints = [i for i, s in enumerate(sims) if s < avg - threshold]

    chunks = []
    start = 0

    for bp in breakpoints:
        chunks.append(" ".join(sentences[start:bp + 1]))
        start = bp + 1

    chunks.append(" ".join(sentences[start:]))

    return [c for c in chunks if c.strip()]


# =========================
# 4. CHUNK PIPELINE
# =========================
def chunk_documents(folder_path: str) -> List[Dict]:
    folder = Path(folder_path)
    results = []

    for file_path in folder.glob("*.txt"):
        raw = file_path.read_text(encoding="utf-8")

        metadata, content = extract_metadata(raw)
        sections = split_sections(content)

        for sec_id, (sec_title, sec_content) in enumerate(sections):
            paragraphs = split_paragraphs(sec_content)

            for para_id, para in enumerate(paragraphs):
                chunks = semantic_chunk(para)

                for chunk_id, chunk in enumerate(chunks):
                    results.append({
                        "id": str(uuid.uuid4()),
                        "text": chunk,
                        "metadata": {
                            **metadata,
                            "section": sec_title,
                            "section_id": sec_id,
                            "paragraph_id": para_id,
                            "chunk_id": chunk_id,
                            "file_name": file_path.name
                        }
                    })

    return results


# =========================
# 5. SAVE JSONL
# =========================
def save_chunks(chunks: List[Dict], path="chunks.jsonl"):
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


# =========================
# 6. EMBEDDING
# =========================
def embed_chunks(chunks: List[Dict]):
    texts = [c["text"] for c in chunks]

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True
    )

    embeddings = np.array(embeddings).astype("float32")

    # 🔥 IMPORTANT
    faiss.normalize_L2(embeddings)

    return embeddings


# =========================
# 7. FAISS IVF + HNSW
# =========================
def build_ivf_hnsw_index(embeddings):
    dim = embeddings.shape[1]
    n = len(embeddings)

    # dynamic nlist
    nlist = int(np.sqrt(n))

    print(f"🔧 Building IVF+HNSW index (nlist={nlist})")

    # HNSW quantizer
    quantizer = faiss.IndexHNSWFlat(dim, 32)
    quantizer.hnsw.efConstruction = 200
    quantizer.hnsw.efSearch = 50

    # IVF
    index = faiss.IndexIVFFlat(quantizer, dim, nlist)

    # train
    index.train(embeddings)

    # add vectors
    index.add(embeddings)

    # search params (set sẵn cho sau này)
    index.nprobe = 10

    return index


# =========================
# 8. SAVE / LOAD
# =========================
def save_index(index, path="faiss.index"):
    faiss.write_index(index, path)


def save_metadata(chunks, path="chunks_meta.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)


# =========================
# 9. MAIN PIPELINE
# =========================
def build_vector_db(folder_path: str):
    # 1. Chunk
    chunks = chunk_documents(folder_path)
    print(f"✅ Total chunks: {len(chunks)}")

    save_chunks(chunks)

    # 2. Embed
    embeddings = embed_chunks(chunks)

    # 3. Build index
    index = build_ivf_hnsw_index(embeddings)

    # 4. Save
    save_index(index)
    save_metadata(chunks)

    print("✅ FAISS index + metadata saved")

    return index, chunks


# =========================
# RUN
# =========================
if __name__ == "__main__":
    index, chunks = build_vector_db("data/docs")