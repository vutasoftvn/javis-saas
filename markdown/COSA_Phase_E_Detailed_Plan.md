# Kế Hoạch Triển Khai Chi Tiết: Phase E (Backend & Frontend)
## Sản Phẩm Bàn Giao (Work Products Contract) & Nhật Ký Quyết Định Kiến Trúc (Decision Records - ADR)

- **Trạng thái:** Bản kế hoạch chính thức (Ready for Implementation)
- **Tài liệu tham chiếu:** `markdown/D3-COSA_Paperclip_Agent_Workforce_Integration.md` (Mục 25, 26, 27, 28, 52)
- **Phạm vi:** Backend (FastAPI + SQLAlchemy) & Frontend (Flutter + GetX)

---

## 1. NGUYÊN TẮC KIẾN TRÚC & QUY TẮC BẮT BUỘC TRONG PHASE E

```mermaid
graph TD
    TaskExec[Agent Thực Thi Tác Vụ] --> ProduceWP[1. Sinh Work Product Theo Hợp Đồng Chuẩn]
    
    ProduceWP --> WPStatus{Trạng thái Ban Đầu: DRAFT / IN_REVIEW}
    
    WPStatus --> HumanReview[Founder / Lead Xem Xét trên Flutter UI]
    
    HumanReview -->|1. Chấp Nhận (Accept)| WPAccepted[Trạng thái: ACCEPTED]
    HumanReview -->|2. Yêu Cầu Sửa (Request Revision)| WPRevise[Gửi Phản Hồi -> Agent Tự Chỉnh Sửa]
    HumanReview -->|3. Từ Chối (Reject)| WPTerminated[Trạng thái: REJECTED]
    
    WPAccepted --> HasDecision{Có Quyết Định Trọng Yếu?}
    HasDecision -->|Có| ADRLog[2. Ghi Nhận Decision Record ADR: Context, Decision, Consequences]
    ADRLog --> ADRListing[Bảng Tra Cứu Quyết Định Kiến Trúc Doanh Nghiệp]
```

### 1.1. Các Quy Tắc Cốt Lõi:
1. **Hướng Sản Phẩm Bàn Giao (Deliverable-Centric, Not Chat-Centric)**: Công việc trong doanh nghiệp không phải là tin nhắn trò chuyện vô định hình mà phải cô đọng thành các **Work Products** có cấu trúc kiểu rõ ràng (`Document`, `Report`, `Spreadsheet`, `CodePatch`, `DecisionRecord`, `CampaignProposal`).
2. **Hợp Đồng Dữ Liệu (Work Product Contract)**:
   - `id`, `title`, `product_type`, `status` (`draft`, `in_review`, `accepted`, `rejected`, `revision_requested`), `author_agent_key`, `content_jsonb`, `metadata_jsonb`.
3. **Vòng Lặp Phản Hồi Đánh Giá (Review Loop)**:
   - Founder/Lead có thể: 🟢 **Accept** (Nghiệm thu) | 🟡 **Request Revision** (Yêu cầu Agent viết lại kèm góp ý cụ thể) | 🔴 **Reject** (Từ chối).
4. **Nhật Ký Quyết Định Kiến Trúc / Chiến Lược (Decision Records - ADR)**:
   - Ghi nhận các quyết định quan trọng của Founder/Agent: `title`, `context_summary`, `decision_content`, `consequences` (hệ quả/tác động), `alternatives_considered` (các phương án đã cân nhắc), `status` (`PROPOSED`, `ACCEPTED`, `SUPERSEDED`).

---

## 2. THIẾT KẾ BACKEND (FASTAPI + SQLALCHEMY)

### 2.1. Service Layer (`backend/app/agent_platform/work_product/`)
1. **`work_product_service.py` (`WorkProductService`)**:
   - `create_work_product(task_id, agent_key, product_type, title, content, workspace_id) -> WorkProduct`
   - `list_work_products(workspace_id, task_id, agent_key, status) -> List[WorkProduct]`
   - `get_work_product(product_id) -> WorkProduct`
   - `accept_work_product(product_id, reviewed_by, feedback) -> WorkProduct`
   - `request_revision(product_id, reviewed_by, feedback) -> WorkProduct`
2. **`decision_service.py` (`DecisionRecordService`)**:
   - `create_decision_record(title, context_summary, decision_content, consequences, alternatives, author_agent_key, workspace_id) -> DecisionRecord`
   - `list_decisions(workspace_id, status) -> List[DecisionRecord]`
   - `accept_decision(decision_id, user_id) -> DecisionRecord`

### 2.2. REST APIs (`backend/app/agent_platform/api/admin_api.py`)
- `GET /api/v1/agent-platform/work-products`: Lấy danh sách sản phẩm bàn giao.
- `GET /api/v1/agent-platform/work-products/{id}`: Chi tiết sản phẩm bàn giao.
- `POST /api/v1/agent-platform/work-products/{id}/accept`: Nghiệm thu sản phẩm.
- `POST /api/v1/agent-platform/work-products/{id}/revise`: Yêu cầu sửa đổi kèm feedback.
- `GET /api/v1/agent-platform/decisions`: Tra cứu danh sách các Decision Records (ADR).
- `POST /api/v1/agent-platform/decisions`: Tạo mới một Decision Record.
- `POST /api/v1/agent-platform/decisions/{id}/accept`: Phê duyệt quyết định ADR.

---

## 3. THIẾT KẾ FRONTEND (FLUTTER + GETX)

### 3.1. Phân Hệ Quản Lý Work Products & Decision Records (ADR)
- **`agent_platform_service.dart`**:
  - `listWorkProducts()`, `acceptWorkProduct()`, `requestWorkProductRevision()`, `listDecisions()`, `acceptDecision()`.
- **Giao diện Nghiệm Thu Sản Phẩm Bàn Giao (`work_product_viewer_dialog.dart`)**:
  - Xem nội dung văn bản / JSON / Markdown của Work Product.
  - Thanh nút thao tác: 🟢 **Nghiệm thu (Accept)** / 🟡 **Yêu cầu làm lại (Request Revision)** kèm modal nhập feedback.
- **Giao diện Sổ Nhật Ký Quyết Định ADR (`decision_records_dialog.dart`)**:
  - Hiển thị danh mục các quyết định chiến lược/kiến trúc: Context, Quyết định, Hệ quả, Các phương án thay thế.

---

## 4. KẾ HOẠCH TEST SUITE CHO PHASE E

### 4.1. Backend Tests (`backend/app/tests/agent_platform/test_cosa_phase_e_work_product.py`):
1. `test_work_product_creation_and_review_lifecycle`: Tạo Work Product $\rightarrow$ In Review $\rightarrow$ Accept hoặc Request Revision thành công.
2. `test_decision_record_adr_lifecycle`: Tạo Decision Record $\rightarrow$ Proposed $\rightarrow$ Accept thành công.

### 4.2. Frontend Tests:
1. `flutter analyze` xác nhận sạch 100% không có lỗi.
