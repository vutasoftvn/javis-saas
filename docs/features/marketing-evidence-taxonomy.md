# Marketing Evidence & Provenance Taxonomy

**Ngày lập:** 2026-08-28  
**Phần của:** [Chương trình tích hợp marketingskills + makerskills vào COSA](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §6  
**Áp dụng:** 18 skillpack, Part CTX (`marketing_context_evidence`), Part SEARCH (Tavily payload provenance)

---

## 1. Mục đích

Tài liệu này chuẩn hoá taxonomy dữ liệu về bằng chứng (evidence) và nguồn gốc xuất xứ (provenance) áp dụng nhất quán trong toàn bộ COSA Marketing & Strategy domain. 

Mọi insight, trích dẫn nghiên cứu thị trường, hồ sơ đối thủ cạnh tranh, phân tích khách hàng và định vị sản phẩm đều phải mang theo metadata evidence để đảm bảo:
- Phân định rõ ràng giữa **sự thật đã kiểm chứng (facts)** và **giả định/suy luận (inferences/assumptions)**.
- Dữ liệu thu thập từ bên ngoài (web, tin tức, tài liệu đối thủ) không bị coi là chỉ thị an toàn hoặc sự thật mặc định (untrusted data protection).
- Người dùng có thể truy nguyên nguồn gốc, ngày thu thập, độ tin cậy và trạng thái duyệt trước khi ghi nhận vào business context chính thức.

---

## 2. Định nghĩa các trường chuẩn (Canonical Fields)

| Tên trường | Kiểu dữ liệu | Giá trị hợp lệ / Format | Mô tả |
| --- | --- | --- | --- |
| `evidence_id` | `string` | UUIDv4 (vd: `f47ac10b-58cc-4372-a567-0e02b2c3d479`) | Định danh duy nhất của bản ghi bằng chứng / trích dẫn. |
| `workspace_id` | `string` | ID workspace (vd: `ws_default` hoặc số nguyên chuỗi hoá) | Không gian làm việc sở hữu dữ liệu (bắt buộc phân lập tenant). |
| `source_url` | `string \| null` | URL hợp lệ (vd: `https://example.com/pricing`) | Đường dẫn nguồn gốc nơi thu thập dữ liệu (nếu có từ web/external). |
| `captured_at` | `string` | ISO 8601 UTC (vd: `2026-08-28T09:00:00Z`) | Thời điểm thu thập dữ liệu. |
| `captured_by` | `string` | `agent:<id>` \| `user:<id>` \| `provider:<name>` | Tác nhân thực hiện thu thập (agent, user hoặc adapter). |
| `confidence` | `string` | `low` \| `medium` \| `high` | Mức độ tự tin về tính xác thực của thông tin trích xuất. |
| `trust` | `string` | `unreviewed` \| `verified` \| `deprecated` \| `superseded` | Mức độ tin cậy được gán sau quá trình kiểm duyệt hoặc vòng đời. |
| `sensitivity` | `string` | `public` \| `internal` \| `confidential` | Phân loại mức độ nhạy cảm của dữ liệu. |
| `review_status` | `string` | `pending` \| `approved` \| `rejected` \| `needs_revision` | Trạng thái phê duyệt của con người/chuyên gia. |
| `supersedes` | `string \| null` | `evidence_id` của bản ghi bị thay thế | Trỏ đến bằng chứng cũ nếu bản ghi này thay thế dữ liệu trước đó. |

---

## 3. Ánh xạ sang Knowledge Document (`packages/agent/knowledge/models.py`)

Taxonomy này **bổ sung** metadata chuyên sâu cho evidence/provenance, **không thay thế** cấu trúc `KnowledgeDocument` hiện có của nền tảng COSA.

### 3.1. Ánh xạ với `authority_class`

| Thuộc tính Taxonomy | Giá trị Taxonomy | `KnowledgeDocument.authority_class` tương ứng | Ý nghĩa |
| --- | --- | --- | --- |
| `sensitivity: public`, `source_url != null` | `trust: unreviewed` | `EXTERNAL` | Dữ liệu thu thập từ web/nguồn ngoài, chưa qua kiểm duyệt. |
| `sensitivity: public`, `source_url != null` | `trust: verified` | `EXTERNAL` | Dữ liệu web đã được nhân sự kiểm tra và xác nhận. |
| `sensitivity: internal/confidential` | `captured_by: agent:*` | `BUSINESS_SNAPSHOT` | Báo cáo, tóm lược phân tích do agent tạo ra trong workspace. |
| `sensitivity: internal` | `trust: verified`, `review_status: approved` | `REFERENCE` | Tài liệu chuẩn nội bộ doanh nghiệp (định vị, persona đã chốt). |
| `sensitivity: confidential` | `review_status: approved` | `POLICY` | Quy định, chính sách, quy chuẩn nội bộ bắt buộc tuân thủ. |
| `captured_by: user:*` | `trust: unreviewed / verified` | `USER_CONTENT` | Nội dung ghi chú, câu trả lời do người dùng tải lên trực tiếp. |

### 3.2. Ánh xạ với `ingest_status`

| `review_status` (Taxonomy) | `trust` (Taxonomy) | `KnowledgeDocument.ingest_status` |
| --- | --- | --- |
| `pending` | `unreviewed` | `review_pending` |
| `approved` | `verified` | `published` |
| `rejected` | `deprecated` / `superseded` | `rejected` |

---

## 4. Nguyên tắc tiêu thụ trong các Part

1. **Part CTX (`commercial.marketing_contexts` & `marketing_context_evidence`):**
   - Lưu trữ các trường này trong bảng quan hệ / payload canonical để truy vấn lọc theo `confidence >= high`, `trust == verified`, hoặc kiểm tra recency theo `captured_at`.
   - Mọi đề xuất cập nhật Marketing Context từ agent đều khởi tạo ở trạng thái `review_status: pending`, `trust: unreviewed`.
2. **Part SEARCH (Tavily production adapter):**
   - Payload trả về từ search provider được chuẩn hoá trực tiếp sang schema provenance này:
     `source_url`, `captured_at` (now), `captured_by: "provider:tavily"`, `confidence: "medium"`, `trust: "unreviewed"`, `sensitivity: "public"`.
   - Kết quả search không bao giờ được đưa thẳng vào system prompt dưới dạng instruction đáng tin cậy.
3. **Skillpacks Nhóm A/B (Part A):**
   - Tất cả template phân tích trong `SKILL.md` (ICP, đối thủ, research brief) phải yêu cầu trích dẫn các trường: `source_url`, `captured_at`, `confidence`, `trust`.
