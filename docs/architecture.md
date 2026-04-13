# Architecture — RAG Pipeline (Day 08 Lab)

> Template: Điền vào các mục này khi hoàn thành từng sprint.
> Deliverable của Documentation Owner.

## 1. Tổng quan kiến trúc

```
[Raw Docs]
    ↓
[index.py: Preprocess → Chunk → Embed → Store]
    ↓
[rag_answer.py: Query → Retrieve → Rerank → Generate]
    ↓
[Grounded Answer + Citation]

```

**Mô tả ngắn gọn:**
> Xây dựng hệ thống RAG để hỗ trợ cho CS và IT Helpdesk, giúp trả lời các câu hỏi chính sách, SLA tickets, quy trình cấp quyền, và FAQ bằng chứng cứ được retrieve có kiểm soát. Giải quyết vấn đề giảm thời gian truy tìm tài liệu càn thiết, đảm bảo tốc độ phản hồi với khách hàng, giảm tải độ nặng công việc của CS và IT Helpdesk

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | TODO |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | TODO |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | TODO |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | TODO |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | TODO |

### Quyết định chunking

| Tham số | Giá trị | Lý do |
|---------|--------|------|
| Chunk size | ~31.8 tokens | Đủ chứa 1 ý hoàn chỉnh (SLA rule, policy block) nhưng vẫn nhỏ để retrieval chính xác |
| Overlap | ~5.45 tokens | Giữ ngữ cảnh giữa các chunk, tránh mất thông tin khi bị cắt |
| Chunking strategy | Heading-based + paragraph-based + semantic chunking | Kết hợp structure (section) và ngữ nghĩa để tránh cắt giữa ý |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter (theo phòng ban), freshness (date), và citation khi trả lời |

---

### Embedding model

- **Model**: sentence-transformers/all-MiniLM-L6-v2  
- **Lý do**:
  - Nhẹ, nhanh (phù hợp real-time retrieval)
  - Hiểu tốt semantic (đủ cho RAG nội bộ)
  - Chi phí thấp (không cần API ngoài)

- **Vector store**: ChromaDB (PersistentClient)  
  - Lưu trữ lâu dài (persistent)
  - Hỗ trợ filter theo metadata
  - Dễ tích hợp với pipeline RAG

- **Similarity metric**: Cosine similarity  
  - Phù hợp với embedding normalized
  - Được FAISS + Chroma hỗ trợ tốt

---

## 3. Retrieval Pipeline (Sprint 2 + 3)

### Baseline (Sprint 2)
| Tham số | Giá trị |
|---------|---------|
| Strategy | Dense (embedding similarity) |
| Top-k search | 10 |
| Top-k select | 3 |
| Rerank | Không |

---

### Variant (Sprint 3)
| Tham số | Giá trị | Thay đổi so với baseline |
|---------|---------|------------------------|
| Strategy | Hybrid (Dense + BM25, alpha=0.5) | Kết hợp semantic + lexical |
| Top-k search | 10 (dense) + toàn bộ BM25 | Hybrid lấy dense top_k*2 + BM25 full corpus |
| Top-k select | 5 | Tăng số context đưa vào answer |
| Rerank | Cross-encoder (ms-marco MiniLM) | Thêm bước rerank để refine |
| Query transform | Không | Không có bước transform |

---

### **Lý do chọn variant này:**

> Chọn hybrid retrieval vì hệ thống cần xử lý cả câu hỏi tự nhiên (policy, SOP) và các token đặc thù như "P1", "ERR-403", nơi dense embedding có thể không match chính xác nhưng BM25 lại làm tốt. Việc kết hợp hai tín hiệu giúp tăng recall ở bước retrieval. Sau đó, sử dụng cross-encoder reranker để sắp xếp lại candidate theo ngữ cảnh đầy đủ giúp cải thiện precision, đảm bảo các đoạn context quan trọng nhất được đưa vào bước sinh câu trả lời.

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
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

user_prompt = f"""
Context:
{context_text}

Question:
{query}
"""
```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
| Model | qwen-3-32B |
| Temperature | 0.1 (để output ổn định cho eval) |
| Max tokens | 512 |

---

## 5. Failure Mode Checklist

> Dùng khi debug — kiểm tra lần lượt: index → retrieval → generation

| Failure Mode | Triệu chứng | Cách kiểm tra |
|-------------|-------------|---------------|


---

## 6. Diagram (tùy chọn)

```mermaid
graph LR
    A[User Query] --> B[Query Encoding - MiniLM]

    %% Retrieval Branch
    B --> C1[Dense Search - FAISS]
    A --> C2[BM25 Search]

    C1 --> D[Combine Scores (Hybrid)]
    C2 --> D

    D --> E[Top-K Candidates (k*2)]

    %% Rerank
    E --> F[Cross-Encoder Rerank]
    F --> G[Top-K Selected Contexts]

    %% Generation
    G --> H[Build Context + Metadata]
    H --> I[LLM - Groq Qwen3]

    %% Output
    I --> J[Answer + Citations]
```