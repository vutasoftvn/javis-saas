// Task 3 (Truthful MVP Hardening) — ControlPlaneService trước đây gọi các
// route không canonical (`/agent/goals`, `/agent/plans/*`, `/agent/runs`,
// `/agents/approvals`). Không route nào trong số này tồn tại ở backend thật
// (`apps/cosa/api/workforce_routes.py`), nên mọi "success" mà class này từng
// trả về trên thực tế là dữ liệu rỗng giả tạo khi gặp 404. Chức năng tương
// đương thật sự (runs, run events, approvals, quyết định approval) đã
// chuyển hẳn sang `WorkforceMvpService`
// (`frontend/lib/modules/workforce/services/workforce_mvp_service.dart`),
// xây trên `MvpRequestClient` để không còn khả năng biến lỗi thành thành
// công giả. Giữ lại class rỗng ở đây để tránh phá vỡ import còn sót lại
// ngoài phạm vi Task 3; không thêm method mới vào class này.
class ControlPlaneService {
  const ControlPlaneService();
}
