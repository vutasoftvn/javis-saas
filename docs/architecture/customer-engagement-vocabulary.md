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

---

## 4. P2 — Channels, Outbound Relay & CRM Identity Sync

### 4.1. Thuật ngữ kênh ngoại vi
| Thuật ngữ | Định nghĩa |
| --- | --- |
| **Channel Endpoint** | Cổng kết nối vật lý với provider ngoại vi (`engagement_channel_endpoints`), liên kết với 1 Inbox, xác định `connector_key`, `inbound_routing_key` và `verification_config_ref`. |
| **Channel Adapter** | Interface độc lập (`ChannelAdapter`) hiện thực hoá việc xác thực chữ ký, chuẩn hoá payload inbound/outbound và truy vấn trạng thái phân phát cho từng nhà cung cấp (API, Zalo OA, Email, SMS). |
| **Double Deduplication** | Cơ chế chống trùng 2 lớp: Lớp 1 chặn trùng `(endpoint_id, provider_delivery_id)` tại `engagement_channel_inbound_events`; Lớp 2 chặn trùng `(workspace_id, external_message_id)` tại `engagement_messages`. |
| **Connector Grant** | Khẳng định quyền truy cập kênh từ Control Plane (`POST /cosa/connectors/assert`), kiểm tra fail-closed hành động `send` trước khi phân giải secret. |
| **Channel Secret Seam** | Cơ chế phân giải token an toàn qua `resolveChannelSecret(secretRef)`; token chỉ tồn tại trong scope hàm gọi provider, **tuyệt đối không bao giờ được lưu vào DB hoặc ghi vào log**. |
| **Identity Review Item** | Yêu cầu xem xét nhận diện khách hàng (`engagement_identity_review_items`) khi tín hiệu nhận diện từ kênh bị nhập nhằng hoặc xung đột (vd: nhiều Contact cùng số điện thoại). |
| **Assumed Delivered** | Trạng thái đối soát ngoại suy sau 24h đối với provider không trả về delivery report cụ thể. |

### 4.2. Nguyên tắc an toàn kênh (Channel Safety Invariants)
1. **Timing-Safe Inbound Verification**: Toàn bộ webhook nhận vào phải được tính toán HMAC SHA-256 trên **raw buffer** và so sánh qua hàm so sánh an toàn thời gian `crypto.timingSafeEqual`. Chữ ký sai hoặc timestamp lệch quá `skewSeconds` trả về `401 Unauthorized` ngay lập tức.
2. **Fail-Closed Channel Activation**: Endpoint chỉ chuyển sang trạng thái `active` khi đã xác thực thành công cả Verification Config và Connector Grant tại thời điểm kích hoạt.
3. **No-Merge CRM Rule**: Khi đồng bộ danh tính từ kênh vào CRM:
   - Khớp 1-1 với Contact đã xác minh: Gắn `contact_id` + `account_id` vào Thread.
   - Nhập nhằng / nhiều kết quả: Giữ `contact_id: null` trên Thread và tạo `engagement_identity_review_items`.
   - Không khớp + bật `auto_create_contact`: Tạo Contact mới với `source=engagement:<channel>`.
   - **Tuyệt đối không bao giờ tự động gộp (merge) hoặc ghi đè các Contact sẵn có**.
4. **Takeover Drop**: Khi nhân viên Desk tiếp quản (`takeover`) hoặc huỷ tin, các bản ghi outbound delivery đang chờ trong hàng đợi relay sẽ bị huỷ bỏ ngay lập tức trước khi gọi provider ngoại vi.

---

## 5. P3 — Deterministic Automation

### 5.1. Thuật ngữ tự động hoá xác định
| Thuật ngữ | Định nghĩa |
| --- | --- |
| **Automation Facts** | Mô hình dữ liệu phẳng có cấu trúc (`AutomationFacts`) trích xuất từ trạng thái thực tế của Thread, Inbox, SLA, Contact, Customer, Last Message, CSAT và Labels tại thời điểm kích hoạt. |
| **Predicate Tree** | Cây điều kiện logic phân cấp (`all`, `any`, `not`, `{ fact, op, value }`) thực thi thuần túy, không có I/O hoặc side-effect. |
| **Automation Rule** | Định nghĩa luật phiên bản hoá (`engagement_automation_rules`), gồm `rule_key`, `version`, `trigger`, `priority`, `condition`, `actions`, `enabled` và `stop_on_match`. |
| **Application Ledger** | Bảng ghi vết thực thi (`engagement_automation_applications`), đảm bảo idempotency trên `(rule_key, rule_version, thread_id, action_index, dedupe_key)`. |
| **Delayed Schedule** | Lịch thực hiện hành động trễ (`engagement_automation_schedules`), yêu cầu re-check fact, condition, ownership và rule status trước khi thực thi tại thời điểm đáo hạn. |

### 5.2. Trạng thái kết quả áp dụng (`outcome`)
- `applied`: Áp dụng hành động thành công qua tầng command của P0.
- `already_applied`: Đã áp dụng trước đó (idempotency hit), không thực hiện lại.
- `skipped_condition_changed`: Điều kiện không còn đúng khi đến hạn lịch hẹn.
- `skipped_ownership_changed`: Nhân viên đã tiếp quản thread (`human_assigned`).
- `skipped_rule_disabled`: Rule đã bị tắt (`enabled: false`) trước khi đến hạn.
- `skipped_no_authority`: Không tìm thấy thẩm quyền tương ứng ở trạng thái `enabled` (fail-closed DR).
- `error`: Lỗi thực thi action.
