# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hoàng Ngọc Thạch - 2A202600068
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/04/2026

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi chủ yếu phụ trách **Sprint 4 — Đánh giá pipeline bằng scorecard, A/B comparison**, tập trung vào xây dựng pipeline đánh giá chất lượng hệ thống RAG. Cụ thể, tôi implement hai phương pháp đánh giá:

- **Heuristic evaluation** (`eval.py`): định nghĩa 4 metrics gồm `faithfulness` (câu trả lời bám vào context), `answer_relevance` (liên quan đến câu hỏi), `context_recall` (context chứa đủ keyword kỳ vọng), và `completeness` (câu trả lời đủ keyword). Pipeline so sánh ba variant: Dense, Hybrid, và Hybrid + Rerank.

- **LLM-as-a-judge** (`eval_grading.py`): sử dụng GPT model để chấm điểm dựa trên rubric 4 mức — Full (100%), Partial (50%), Zero (0%), Penalty (-50% nếu hallucinate). Kết quả chấm theo từng câu hỏi trong `grading_questions.json`, output ra `grading_scores.json`.

Ngoài ra, tôi viết `run_grading.py` để chạy toàn bộ pipeline retrieval + generation với mode **hybrid + rerank** trên 10 câu hỏi grading, lưu câu trả lời vào `grading_results.json` làm đầu vào cho bước chấm điểm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau lab này, tôi hiểu rõ hơn về **sự khác biệt giữa heuristic evaluation và LLM-as-a-judge**. Heuristic (keyword matching) cho điểm hệ thống rất thấp (~36.7%), trong khi LLM judge cho ~63.3% — chênh lệch 26.6 điểm phần trăm. Nguyên nhân là heuristic không hiểu được paraphrase và semantic match: câu trả lời đúng nghĩa nhưng dùng từ khác hoàn toàn có thể bị tính là sai.

Điều này cho thấy **lựa chọn metric đánh giá ảnh hưởng lớn đến nhận định về chất lượng hệ thống**. Nếu chỉ dùng heuristic, ta sẽ kết luận sai rằng pipeline rất kém và tập trung cải thiện sai chỗ. LLM judge gần với human grading hơn và phản ánh đúng bản chất chất lượng của câu trả lời.

Ngoài ra, tôi cũng hiểu rõ hơn về **cách thiết kế rubric chấm điểm**. Việc định nghĩa rõ ràng criteria, failure mode, và từng mốc điểm (Full/Partial/Zero/Penalty) giúp LLM judge nhất quán và ít bị drift hơn khi chấm nhiều câu.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều khiến tôi ngạc nhiên nhất là **metric `context_recall` không thay đổi giữa các variant** — cả Dense, Hybrid, Hybrid + Rerank đều cho cùng giá trị 0.195. Ban đầu tôi nghĩ hybrid + rerank sẽ cải thiện rõ rệt recall, nhưng thực tế là cách tính chỉ đếm từ có xuất hiện hay không, nên dù ba variant retrieve các chunk khác nhau, kết quả vẫn như nhau. Chỉ có `relevance` và `completeness` mới thấy sự cải thiện rõ (từ 0.33 → 0.53 và từ 0.43 → 0.62 khi qua hybrid + rerank).

Khó khăn lớn nhất là **thiết kế prompt cho LLM judge** để output đúng JSON format. Model đôi khi trả về text mô tả thêm bên ngoài JSON block, khiến `json.loads()` bị lỗi. Tôi phải thêm fallback để trả về `Zero` khi parse thất bại. Ngoài ra, với câu hỏi không có ground truth rõ ràng (như gq07 — "abstain behavior"), việc định nghĩa criteria phải rất cụ thể để tránh judge bị nhầm.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq05 — Contractor từ bên ngoài có được cấp Admin Access không?

**Phân tích:**

Đây là câu hỏi bị **Zero (0/10)** — lỗi nặng nhất bên cạnh Penalty. Khi phân tích, vấn đề chính nằm ở bước **retrieval không đủ coverage**. Câu hỏi yêu cầu tổng hợp từ hai section khác nhau trong `it/access-control-sop.md`: Section 1 (phạm vi áp dụng — contractor được bao gồm) và Section 2 (chi tiết Level 4 — approver là IT Manager + CISO, 5 ngày xử lý, training bắt buộc).

Pipeline hybrid + rerank chỉ retrieve được các chunk liên quan đến quy trình xử lý (Section 3, 4) nhưng bỏ sót Section 1 nơi khai báo rằng contractor thuộc phạm vi áp dụng. Do đó, LLM không có đủ context để xác nhận contractor được cấp quyền, và đã trả lời "Không tìm thấy trong tài liệu" — đúng về mặt faithfulness nhưng sai về mặt factual.

So sánh với gq06 cũng là cross-doc nhưng đạt Partial (6/12): gq06 còn retrieve được 1 phần context từ đúng file, trong khi gq05 không retrieve được chunk quyết định (Section 1). Điều này cho thấy **chunking nhỏ (~32 tokens) gây mất thông tin liên tục**, khiến scope declaration bị tách rời khỏi detail và không được retrieve cùng nhau.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thay thế keyword matching bằng **embedding-based similarity** để đo `context_recall` và `completeness` chính xác hơn, tránh false negative do paraphrase. Ngoài ra, tôi muốn thêm **per-question analysis** vào pipeline evaluation — không chỉ aggregate metrics mà còn chỉ ra cụ thể câu nào fail và fail ở bước nào (retrieve hay generate). Điều này giúp debug nhanh hơn và đưa ra cải tiến có mục tiêu thay vì cải thiện chung chung.
