# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**

retrieval_mode = "dense"
chunk_size = ~32 tokens
overlap = ~5 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = qwen/qwen3-32b


**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 1.45 /5 |
| Answer Relevance | 1.65 /5 |
| Context Recall | 1.00 /5 |
| Completeness | 2.15 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- q07 (Approval Matrix alias) → context recall thấp do dense không match tên cũ
- q09 (ERR-403-AUTH) → không có context → model vẫn trả lời → faithfulness thấp
- q03 (Level 3 approval) → thiếu đủ entity → answer thiếu (completeness thấp)

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias  
- [x] Retrieval: Top-k quá ít → thiếu evidence  
- [x] Generation: Prompt chưa enforce đủ mạnh việc abstain  
- [ ] Indexing: Chunking cắt giữa điều khoản  
- [ ] Generation: Context quá dài → lost in the middle  

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** Retrieval strategy → Hybrid (Dense + BM25)  

**Lý do chọn biến này:**
> Baseline cho thấy nhiều câu thất bại do dense retrieval không match được keyword đặc thù như "P1", "ERR-403", hoặc alias (q07).  
> Corpus chứa cả text tự nhiên (policy) và token đặc biệt (mã lỗi, SLA label), nên cần thêm BM25 để tăng recall.

**Config thay đổi:**

retrieval_mode = "hybrid"
top_k_search = 10 (dense) + BM25 full corpus
top_k_select = 5
use_rerank = False


**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 1.45 | 1.45 | 0.00 |
| Answer Relevance | 1.65 | 2.30 | +0.65 |
| Context Recall | 1.00 | 1.00 | 0.00 |
| Completeness | 2.15 | 2.90 | +0.75 |

**Nhận xét:**
- Cải thiện rõ ở các câu có keyword cụ thể (SLA, policy)
- Completeness tăng do retrieve được nhiều context đúng hơn
- Faithfulness không đổi → model vẫn hallucinate nhẹ
- Context recall không cải thiện → do chunking + keyword metric hạn chế

**Kết luận:**
> Hybrid tốt hơn baseline rõ rệt về Answer Relevance và Completeness.  
> Cho thấy retrieval là bottleneck chính trong hệ thống.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Thêm Rerank (Cross-Encoder)  

**Config:**

retrieval_mode = "hybrid"
top_k_search = 10
top_k_select = 5
use_rerank = True


**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 1.45 | 1.45 | 1.50 | Variant 2 |
| Answer Relevance | 1.65 | 2.30 | 2.65 | Variant 2 |
| Context Recall | 1.00 | 1.00 | 1.00 | Tie |
| Completeness | 2.15 | 2.90 | 3.10 | Variant 2 |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Retrieval miss (dense không bắt được keyword/alias), dẫn tới thiếu context → answer sai hoặc thiếu.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Retrieval strategy (Dense → Hybrid) có impact lớn nhất, đặc biệt lên Answer Relevance và Completeness.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > 
   > - Tăng chunk size (~100–200 tokens) để cải thiện context recall  
   > - Thêm query expansion (HyDE hoặc synonym)  
   > - Improve abstain logic để tăng faithfulness  