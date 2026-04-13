| ID   | Grade    | Score |
|------|----------|-------|
| gq01 | Full     | 10 / 10 |
| gq02 | Penalty  | -5 / 10 |
| gq03 | Full     | 10 / 10 |
| gq04 | Full     | 8 / 8 |
| gq05 | Zero     | 0 / 10 |
| gq06 | Partial  | 6 / 12 |
| gq07 | Full     | 10 / 10 |
| gq08 | Partial  | 5 / 10 |
| gq09 | Full     | 8 / 8 |
| gq10 | Full     | 10 / 10 |

---

### Tổng điểm

- **Total Score:** 62 / 98  
- **Percentage:** **63.27%**

 Quy đổi:

Grading Score = (62 / 98) × 30 ≈ 18.98 / 30


---

## So sánh với heuristic scoring

| Metric | Heuristic | LLM Judge | Delta |
|--------|----------|-----------|-------|
| Total Score | 36 | 62 | **+26** |
| Percentage | 36.7% | 63.3% | **+26.6%** |

### Insight
- Heuristic **đánh giá thấp** do:
  - không hiểu paraphrase
  - miss semantic match
- LLM Judge phản ánh **gần với human grading hơn**

---

## Phân tích kết quả

### 1. Điểm mạnh

#### High accuracy on factual + temporal questions
- gq01, gq03, gq04, gq07, gq09, gq10 → **Full**
- Pipeline làm tốt:
  - version comparison (gq01)
  - exception handling (gq03)
  - numeric extraction (gq04, gq09)
  - temporal reasoning (gq10)
  - abstain đúng (gq07)

👉 Cho thấy:
- retrieval + rerank hoạt động ổn định với câu hỏi rõ ràng
- LLM generate đúng khi context đủ

---

### 2. Lỗi nghiêm trọng

#### gq02 — Penalty (-5)
- Multi-document (remote + VPN + device)
- Pipeline:
  - retrieve thiếu hoặc sai context
  - **vẫn generate → hallucination**
- → lỗi critical nhất

---

#### gq05 — Zero
- Multi-condition + multi-section
- Thiếu:
  - approver
  - điều kiện
  - thời gian
- → retrieval không đủ coverage

---

### 3. Các lỗi trung bình

#### gq06 — Partial (6/12)
- Cross-doc + multi-hop reasoning
- Pipeline:
  - retrieve được 1 phần
  - thiếu flow đầy đủ

---

#### gq08 — Partial
- Disambiguation case
- Answer chưa phân biệt rõ ràng 2 concept

---

## Root Cause Analysis

### 1. Retrieval coverage chưa đủ
- Dù đã dùng hybrid + rerank:
  - vẫn miss multi-doc cases (gq02, gq06)
  - vẫn thiếu detail (gq05)

---

### 2. Chunking chưa tối ưu
- Chunk nhỏ (~32 tokens)
→ bị:
- mất context liên tục
- khó tổng hợp nhiều điều kiện

---

### 3. Hallucination control chưa chặt
- Pipeline chưa:
  - detect thiếu context
  - force abstain

→ dẫn đến penalty (gq02)

---
