# Customer Engagement — Domain Vocabulary & Contracts

Tài liệu chuẩn hoá thuật ngữ, schema và hợp đồng cho phân hệ **Customer Engagement** (Human Desk & AI Copilot).

---

## 1. Tổng quan phân hệ & Kiến trúc

Customer Engagement quản lý toàn bộ luồng giao tiếp đa kênh giữa khách hàng và doanh nghiệp.
- **P0**: Human Desk — Inbox, Thread, Message, Assignment, SLA, Escalation, Decision Request (hoàn toàn do nhân viên vận hành).
- **P1**: Customer Support Copilot — Hỗ trợ nhân viên trực Desk tại chỗ (chỉ tạo artifact, không gửi tin tự động, không ghi CRM, không kích bằng event).
- **P2–P4**: External Connectors, CRM Sync, Autopilot (Event-driven).

---

## 2. Thuật ngữ cốt lõi (Domain Concepts)

| Thuật ngữ | Định nghĩa |
| --- | --- |
| **Inbox** | Hộp thư tiếp nhận theo kênh/đội ngũ, cấu hình SLA và giờ làm việc. |
| **Thread** | Phiên hội thoại liên tục giữa khách hàng và doanh nghiệp. |
| **Message** | Đơn vị tin nhắn trong thread (`inbound` / `outbound`, `public` / `internal`). |
| **Assignment** | Phân bổ quyền phụ trách thread cho một `WorkforceMember` hoặc Agent. |
| **Decision Request** | Yêu cầu phê duyệt nghiệp vụ có thẩm quyền (giảm giá, hoàn tiền, huỷ hợp đồng). |
| **Copilot Invocation** | Một lượt yêu cầu Copilot phân tích thread và đề xuất bản nháp/tóm tắt cho nhân sự Desk. |

---

## 3. P1 — Customer Support Copilot Contract

### 3.1. Nguyên tắc thiết kế (Design Principles)
- **Artifact-Only**: Copilot chạy ở mức `AutonomyLevel.L0_OBSERVE`. Copilot CHỈ đọc dữ liệu và tạo artifact (`engagement.message.draft`), **tuyệt đối không gửi tin, không ghi CRM, không tự kích hoạt bằng event**.
- **Fail-Closed Enablement**: Mặc định Copilot ở trạng thái tắt (`enabled: false`). Chỉ có thể bật khi workspace đã pin `allowed_agent_spec_id`, `allowed_agent_spec_version`, `allowed_agent_spec_hash` VÀ cung cấp `eval_evidence_ref` tươi có `eval_evidence_hash` khớp với spec hash.
- **Context Tối thiểu hoá**: Context cung cấp cho agent chỉ gồm metadata thread và tin nhắn gần nhất; không chứa CoT; khách hàng chưa xác thực (`identity_verified: false`) sẽ bị che giấu toàn bộ thông tin tài khoản / hoá đơn (PII redaction).

### 3.2. Copilot Panel Fields
Giao diện Desk nhận được payload cấu trúc sau khi Copilot hoàn thành (`run.completed`):
- `summary`: Tóm tắt ngắn gọn nội dung và yêu cầu của khách hàng trong thread.
- `recommended_response_draft`: Bản nháp phản hồi đề xuất cho nhân viên Desk.
- `intent`: Ý định chính của khách hàng (vd: `account_inquiry`, `technical_issue`, `summarize`, `draft_reply`).
- `missing_info`: Danh sách các thông tin còn thiếu cần khách hàng làm rõ.
- `sales_signal`: Tín hiệu cơ hội bán hàng / upsell phát hiện được (nếu có).
- `evidence_refs`: Danh sách các mã tham chiếu bằng chứng trích xuất từ Knowledge Base hoặc nội dung thread (`minItems: 1`).

### 3.3. Invocation Lifecycle States
Trạng thái của bản ghi `engagement_copilot_invocations`:
- `dispatched`: Yêu cầu đã được Company Service tiếp nhận và gửi lệnh schedule sang COSA.
- `running`: Worker đang thực thi run.
- `completed`: Hoàn thành, đã lưu artifact và sẵn sàng hiển thị trên Copilot Panel.
- `failed`: Xảy ra lỗi trong quá trình thực thi.
- `cancelled`: Yêu cầu bị huỷ.

### 3.4. Feedback Values
Nhân viên Desk sau khi tham khảo bản nháp của Copilot gửi phản hồi đánh giá:
- `accepted`: Sử dụng nguyên văn bản nháp của Copilot.
- `edited`: Chỉnh sửa bản nháp trước khi gửi cho khách hàng (lưu kèm `feedback_edited_ref`).
- `rejected`: Không sử dụng bản nháp.

> **Lưu ý:** Việc gửi tin nhắn tới khách hàng luôn do nhân viên Desk thực hiện chủ động qua API `sendPublicMessage` của P0; hệ thống Copilot không tự động chèn tin vào thread khi submit feedback.

### 3.5. Quy trình kích hoạt Copilot (Enablement Checklist)
1. Xác định Spec: `cosa.agents.customer_support` (version `1.0.0`, definition hash tương ứng).
2. Chạy bộ Eval: Thực thi `CanonicalEvalRunner` với `CUSTOMER_SUPPORT_COPILOT_EVAL_CASES` (kiểm tra 4 nhóm: Security PII Redaction, No Unsafe Promise, Evidence Citations, Capability Boundary).
3. Lấy Evidence: Lưu kết quả eval suite và lấy `eval_evidence_ref` + `eval_evidence_hash`.
4. Cập nhật Settings: Gửi `PATCH /commercial/engagement/copilot/settings` với `agentSpecId`, `agentSpecVersion`, `agentSpecHash`, `evalEvidenceRef`, `evalEvidenceHash`.
5. Kích hoạt: Gửi `POST /commercial/engagement/copilot/settings/enable`.
