# Rule: Full-Stack Planning Invariant (Backend + Frontend End-to-End)

## Nguyên Tắc Bắt Buộc Khi Lập Kế Hoạch (Implementation Plan)

1. **Phải Luôn Bao Gồm Cả Backend & Frontend (Full-Stack Scope)**:
   - Mọi bản kế hoạch (`implementation_plan.md`) hoặc đề xuất tính năng mới **bắt buộc phải mô tả đồng thời cả hai phần**:
     - **Backend**: Data Model (SQLAlchemy/PostgreSQL), Business Logic / Service, Governance, API Endpoints, Providers, CLI / Workers.
     - **Frontend (Flutter)**: Data Models / DTOs, API Provider / Repositories, GetX Controller / State Management, Views / Widgets, Micro-interactions và UI/UX Navigation.
   - Tuyệt đối không lập kế hoạch cụt lủn chỉ có Backend mà bỏ quên luồng trải nghiệm người dùng trên Frontend, hoặc ngược lại.

2. **Ánh Xạ Luồng Dữ Liệu Rõ Ràng (Contract-First)**:
   - Phải định nghĩa rõ API Contract (Request/Response payload JSON) kết nối giữa Backend FastAPI và Flutter Client.
   - Frontend phải có cơ chế xử lý phản hồi, trạng thái loading, lỗi (graceful degradation) và cập nhật realtime (qua Polling/SSE/WebSocket).

3. **Tuân Thủ Thiết Kế UI/UX Cao Cấp**:
   - Giao diện Flutter trên Desktop & Mobile phải tuân thủ chuẩn thẩm mỹ cao cấp (Modern Typography, Glassmorphism, Dark Mode, Micro-animations, Hologram HUD).
   - Tuyệt đối tuân thủ quy tắc riêng của Hologram Hub: Không dùng toast/snackbar che khuất màn hình mà sử dụng inline visual state feedback.
