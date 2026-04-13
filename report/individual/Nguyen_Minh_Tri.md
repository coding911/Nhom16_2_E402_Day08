# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Minh Trí  
**Vai trò trong nhóm:** Indexing Owner
**Ngày nộp:** 13/4/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi phụ trách chính phần **indexing** và chuẩn bị dữ liệu cho pipeline RAG. Tôi code file `indexing.py`, thực hiện:
- chia nhỏ tài liệu thành các chunk hợp lý,
- tạo embeddings với FAISS,
- xây dựng chỉ mục truy xuất và lưu trữ metadata cho mỗi chunk.

Công việc của tôi kết nối trực tiếp với `rag_answer.py` của thành viên khác để đảm bảo retrieval nhận được context đầy đủ và chính xác. Đồng thời, tôi làm việc với `eval.py` để xác định các tham số top-k và kiểm tra xem chất lượng index ảnh hưởng như thế nào đến điểm đánh giá cuối cùng.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau lab này, tôi hiểu rõ hơn về **chunking** và tầm quan trọng của nó trong toàn bộ pipeline. Chunk nhỏ quá sẽ làm tăng noise và mất ngữ cảnh; chunk lớn quá lại làm giảm khả năng retrieval chính xác. Tôi cũng thấy rõ rằng chất lượng index không chỉ là embeddings, mà còn liên quan đến metadata, số lượng chunk và cách lựa chọn top-k.

Thêm nữa, tôi hiểu sâu hơn về **mối quan hệ giữa indexing và retrieval**: một index tốt giúp retrieval trả về context liên quan hơn, giảm lỗi hallucination khi `rag_answer.py` sinh câu trả lời. Nếu đoạn văn không được chunk đúng cách, dù model LLM có mạnh cũng vẫn nhận được input thiếu hoặc lặp.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất với tôi là xử lý **chunking cho các tài liệu khác nhau**. Một số file như chính sách HR có cấu trúc câu dài, nhiều điều kiện, trong khi FAQ có câu ngắn gọn. Tạo chunk sao cho vẫn giữ được ý nghĩa, nhưng không quá dài khi đưa vào FAISS là phần mất nhiều thời gian debug nhất.

Tôi cũng ngạc nhiên khi thấy rằng thay đổi nhẹ trong `chunk_size` và `overlap` đã ảnh hưởng rõ rệt đến kết quả retrieval. Ban đầu tôi nghĩ indexing chỉ cần embedding và một số tham số cố định, nhưng thực tế phải thử nhiều giá trị khác nhau để cân bằng giữa recall và precision.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** gq02 — Remote + VPN + giới hạn thiết bị

**Phân tích:**

Ở câu hỏi này, lỗi chính nằm ở bước **indexing/retrieval** chứ không phải generation. Khi phân tích log, tôi thấy pipeline trả về các chunk liên quan đến VPN mà thiếu một số điều kiện về giới hạn thiết bị. Điều đó dẫn đến việc `rag_answer.py` có context không đủ, nên LLM sinh câu trả lời bị thiếu hoặc thêm thông tin không chính xác.

Với baseline hiện tại, câu trả lời sai do thiếu coverage từ index. Variant cải thiện khi tăng `top_k_search` và `top_k_select`, vì nó cho phép retrieval lấy thêm nhiều chunk hơn, giúp bù đắp phần context thiếu. Tuy nhiên, nếu chunk quá nhỏ hoặc overlap quá thấp, hệ thống vẫn mất thông tin nối câu. Vì vậy, bài toán này cho thấy cần cải thiện cả **chunking và số lượng chunk lấy về**, chứ không chỉ thay đổi bộ đánh giá.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ thử thêm hai cải tiến:
1. điều chỉnh `chunk_size` và `overlap` để cân bằng giữa ngữ cảnh và độ chính xác của retrieval,
2. bổ sung `metadata` cho từng chunk để ưu tiên các đoạn chứa keyword quan trọng như “VPN”, “remote access”, “device limit”.

Cải tiến này cụ thể vì kết quả eval cho thấy nhiều lỗi đến từ việc retrieval không lấy đủ context và chunk chứa thông tin quan trọng bị bỏ qua.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*