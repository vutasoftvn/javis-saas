---
id: legal-document-drafting
name: Legal Document Drafting
domain: governance
version: 1.0.0
risk: high
---

# Mục tiêu

Hỗ trợ soạn thảo bản nháp tài liệu quản trị/pháp lý dựa trên dữ liệu company và nguồn pháp lý hiện hành.

# Không được làm

- Không tự khẳng định tài liệu là tư vấn pháp lý cuối cùng.
- Không dùng văn bản pháp luật đã hết hiệu lực nếu có nguồn mới hơn.
- Không thay đổi nội dung Legal Source gốc.
- Không thực thi/publish tài liệu high-risk khi chưa qua policy approval.

# Context được phép

- Company profile
- Company governance configuration
- User-provided transaction/party data
- Active Legal Knowledge Pack

# Quy trình

1. Xác định loại tài liệu.
2. Kiểm tra input bắt buộc.
3. Resolve legal references hiện hành.
4. Resolve company template override; nếu không có dùng factory template.
5. Tạo structured artifact draft.
6. Gắn legal source references và version.
7. Đánh dấu `review_required=true`.

# Output contract

- artifact_type
- title
- sections
- variables_used
- legal_sources
- unresolved_items
- review_required
