# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lại Đức Anh
**Vai trò trong nhóm:** Retrieval Owner 
**Ngày nộp:** 13/4/2026

---

## 1. Tôi đã làm gì trong lab này? 

Trong lab này, tôi chủ yếu phụ trách **Sprint 2 và Sprint 3**, tập trung vào xây dựng pipeline retrieval và đánh giá hệ thống. Cụ thể, tôi implement các phương pháp truy xuất gồm **dense retrieval (FAISS + embedding)** và **hybrid retrieval (kết hợp Dense + BM25)** trong file `rag_answer.py`. Ngoài ra, tôi tích hợp thêm bước **rerank bằng cross-encoder** để cải thiện chất lượng context trước khi đưa vào LLM.

Đánh giá kết quả của grade_questions.json

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau lab này, tôi hiểu rõ hơn về **hybrid retrieval** và vai trò của nó trong RAG pipeline. Trước đây, tôi nghĩ embedding là đủ để tìm thông tin liên quan, nhưng thực tế cho thấy embedding thường bỏ sót các từ khóa quan trọng như mã lỗi hoặc label (ví dụ: “P1”, “ERR-403”). Việc kết hợp với BM25 giúp cải thiện đáng kể khả năng recall trong các trường hợp này.

Ngoài ra, tôi cũng hiểu rõ hơn về mối quan hệ giữa **retrieval và generation**. Nếu retrieval không cung cấp đủ context, thì dù model LLM có mạnh cũng không thể trả lời đúng. Điều này cho thấy retrieval là thành phần quyết định chất lượng đầu ra của toàn hệ thống, chứ không chỉ là bước tiền xử lý.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn 

Điều khiến tôi ngạc nhiên nhất là việc **evaluation bằng heuristic (keyword matching)** cho kết quả rất thấp (~36%), trong khi khi chuyển sang **LLM-as-a-judge**, điểm tăng lên ~63%. Ban đầu tôi nghĩ hệ thống hoạt động kém, nhưng thực tế là cách đánh giá chưa phản ánh đúng chất lượng câu trả lời.

Khó khăn lớn nhất là debug các lỗi liên quan đến retrieval. Khi một câu trả lời sai, rất khó xác định nguyên nhân nằm ở bước retrieve hay generate. Đặc biệt với các câu hỏi cần tổng hợp từ nhiều tài liệu, hệ thống thường retrieve thiếu context nhưng vẫn generate câu trả lời “có vẻ đúng”, dẫn đến hallucination. Điều này làm việc debug mất nhiều thời gian vì phải kiểm tra cả pipeline thay vì chỉ một bước.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq02 — Remote + VPN + giới hạn thiết bị

**Phân tích:**

Ở câu hỏi này, pipeline của nhóm bị **Penalty (-5/10)** do hallucination. Khi phân tích chi tiết, có thể thấy lỗi chính nằm ở bước **retrieval**. Câu hỏi yêu cầu tổng hợp thông tin từ nhiều khía cạnh (remote access, VPN requirement, device limit), nhưng hybrid retrieval chỉ trả về một phần context, chủ yếu liên quan đến VPN.

Sau đó, ở bước rerank, cross-encoder chọn các chunk có độ liên quan cao nhất nhưng vẫn thiếu một số điều kiện quan trọng. Tuy nhiên, LLM không nhận ra việc thiếu thông tin và vẫn generate một câu trả lời đầy đủ, dẫn đến việc “bịa” thêm thông tin không có trong tài liệu.

So với baseline dense, variant hybrid + rerank có cải thiện nhẹ về độ liên quan của context, nhưng vẫn chưa đủ để giải quyết bài toán multi-document. Điều này cho thấy vấn đề chính không phải ở generation mà là **retrieval chưa đủ coverage**. Nếu không tăng số lượng chunk hoặc cải thiện chunking, hệ thống sẽ tiếp tục gặp lỗi tương tự.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ ưu tiên cải thiện **retrieval coverage** bằng cách tăng `top_k_search` và `top_k_select`, vì kết quả evaluation cho thấy nhiều câu fail do thiếu context (gq02, gq05). Ngoài ra, tôi sẽ thử tăng **chunk size** (từ ~32 lên ~100 tokens) để giữ được nhiều thông tin hơn trong mỗi chunk. Cuối cùng, tôi muốn thêm cơ chế **abstain** khi context không đủ, để giảm lỗi hallucination.
