# Kế Hoạch Triển Khai Chi Tiết: Phase 5
## Intelligence Optimization, Legal AI Contract Reviewer, Pattern Learning (L4 Memory) & Multi-Device Hardening

Tài liệu này là thiết kế kỹ thuật chi tiết để triển khai giai đoạn cuối cùng **Phase 5: Intelligence Optimization, Legal AI & Multi-Device Hardening** cho COSA OS.

---

## 1. Mục Tiêu Triển Khai

1. **Legal Agent & AI Contract Reviewer**:
   - Tải lên hoặc dán nội dung văn bản hợp đồng / thỏa thuận $\rightarrow$ AI Legal Specialist tự động trích xuất các điều khoản rủi ro:
     - Rủi ro điều khoản thanh toán & phạt vi phạm (Penalty risks).
     - Rủi ro quyền sở hữu trí tuệ (IP terms) & bảo mật (NDA).
     - Rủi ro quyền chấm dứt đơn phương (Termination rights).
     - Đưa ra đề xuất điều chỉnh điều khoản cụ thể.
   - Quản lý danh mục kiểm tra pháp lý doanh nghiệp (`Legal Checklist`) và nghĩa vụ pháp lý (`Legal Obligations`).
2. **L4 Pattern Learning Memory**:
   - Hệ thống lưu trữ các kinh nghiệm (Lessons Learned) từ chiến dịch Marketing, deal Bán hàng, và quyết định phê duyệt của Founder vào bộ nhớ `L4` trong `agent_memory`.
   - Giúp các AI Agent tự động học hỏi, không lặp lại sai lầm trong các chu kỳ sau.
3. **Multi-Device & Navigation Hardening**:
   - Mở khóa mục **Pháp lý** (Index 22 - `LegalView`) trên Sidebar Dashboard.
   - Hoàn thiện trải nghiệm nhất quán trên Desktop, Tablet và Mobile.
   - Đảm bảo 100% test cases Pytest và Flutter analyze sạch lỗi.

---

## 2. Kiến Trúc & API Endpoints

### 2.1 Backend Routers
- `POST /api/v1/legal/reviews/analyze`: Rà soát và phân tích rủi ro hợp đồng bằng AI.
- `GET /api/v1/legal/checklist`: Danh sách kiểm tra pháp lý.
- `POST /api/v1/legal/checklist`: Thêm hạng mục kiểm tra pháp lý.
- `GET /api/v1/legal/obligations`: Danh sách nghĩa vụ pháp lý.
- `POST /api/v1/legal/obligations`: Tạo nghĩa vụ pháp lý mới.
- `GET /api/v1/workspaces/{workspace_id}/memory/l4-patterns`: Danh sách bài học kinh nghiệm L4 Memory.

---

## 3. Kế Hoạch Kiểm Thử (Verification Plan)

1. **Pytest Backend (`test_p5_legal_and_intelligence.py`)**:
   - `test_legal_cross_tenant_forbidden`
   - `test_contract_risk_analyzer_logic`
   - `test_legal_checklist_and_obligations_crud`
   - `test_l4_pattern_learning_recording`
2. **Toàn Bộ Pytest (P1 + P2 + P3 + P4 + P5)**:
   - Đạt 100% pass (24+ tests).
3. **Frontend Flutter Analysis**:
   - `flutter analyze lib/` đạt 0 lỗi, 0 cảnh báo.
