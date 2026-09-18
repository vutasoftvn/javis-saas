# Decision Log & Actionability Hygiene Playbook

> **Tài liệu tham chiếu chuyên sâu dành cho:** Chief of Staff (CoS) & Decision Engineers  
> **Nguyên tắc cốt lõi:** Nhật ký quyết định bất biến (Immutable Decision Log), Tiêu chí ràng buộc khả thi, Rà soát định kỳ theo tuần.

---

## 1. Cấu Trúc Biên Bản Quyết Định Chuẩn (`BoardroomMemo`)

Mọi cuộc họp chiến lược của Hội đồng C-Suite chỉ được coi là hoàn tất khi sinh ra một `BoardroomMemo` đầy đủ các trường dữ liệu:

1. **`deliberation_id`:** Mã định danh phiên họp duy nhất (UUID/Timestamp).
2. **`question`:** Câu hỏi nghị sự chiến lược đã được đóng khung rõ ràng.
3. **`recommended_option`:** Phương án tối ưu được đề xuất hàng đầu kèm luận cứ.
4. **`vote_tally`:** Bảng phân bổ phiếu bầu minh bạch của từng C-Level (vai trò $\rightarrow$ phương án).
5. **`preserved_dissent`:** Danh sách các tiếng nói bất đồng nguyên văn (`DissentRecord`).
6. **`binding_criteria`:**
   - `success_criteria`: Các chỉ số định lượng đo lường chiến thắng.
   - `kill_criteria`: Các điều kiện dừng dứt khoát nếu gặp rủi ro lớn.
   - `review_checkpoint_week`: Tuần bắt buộc rà soát lại kết quả thực tế (thường là Tuần 06).
7. **`evidence_tag`:** Nhãn độ tươi của bối cảnh Snapshot Startup OS tại thời điểm ra quyết định.

---

## 2. Kỷ Luật Vệ Sinh Nhật Ký Quyết Định (Decision Hygiene)

- **Tính Bất Biến (Immutability):** Khi Founder đã ký duyệt (Status $\rightarrow$ `APPROVED`), nội dung của `BoardroomMemo` KHÔNG ĐƯỢC PHÉP chỉnh sửa.
- **Tránh Thiên Kiến Nhận Thức Muộn (Hindsight Bias):** Sau 12 tuần, khi nhìn lại một quyết định thất bại, việc xem lại `BoardroomMemo` gốc sẽ giúp công ty đánh giá chính xác: "Chúng ta ra quyết định tồi" hay "Chúng ta đã ra quyết định tốt nhất dựa trên dữ liệu lúc đó nhưng gặp rủi ro bất khả kháng?".
