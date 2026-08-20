# COSA Phase 5: Profile & Skill Visual Composition

Tài liệu này mô tả chi tiết kiến trúc của tính năng cấu hình Agent Role thông qua Profile và Skill trong Phase 5.

## Tổng quan
Mục tiêu chính của Phase 5 là chuyển đổi việc định nghĩa vai trò (Role) của Agent từ mã nguồn tĩnh (static turn loops) sang dạng cấu hình linh hoạt (composition) có thể chỉnh sửa thông qua UI, nhưng vẫn phải **bảo vệ chặt chẽ các giới hạn quyền hạn (ExecutionScope) và logic kiểm soát (GovernanceKernel)**.

## 1. Composition Contracts
Các Profile (như Sales, Marketing) được định nghĩa qua `AgentProfile` DTO. Khi một Agent chạy, Profile này không được dùng trực tiếp mà phải đi qua `ProfileCompositionService` để biên dịch thành `ResolvedProfile`.

Quá trình biên dịch này lọc bỏ các cấu hình không hợp lệ:
- Lọc theo **Scope**: Nếu Profile yêu cầu `crm.read` nhưng người dùng chạy Agent không có quyền này, Tool đó bị loại bỏ.
- Lọc theo **Extension**: Nếu Tool thuộc về một extension đang bị vô hiệu hoá.
- Trả về `ProfileExplanation` để UI giải thích lý do tại sao một công cụ/skill không khả dụng.

## 2. Session Overrides (Subtractive)
Người dùng có thể tuỳ chỉnh Agent trong một Session cụ thể (ví dụ: tắt bớt Tool).
Quy tắc vàng: **Session Override is Monotonic Subtractive**.
- Nó chỉ có thể *xoá bớt* Tool, Skill, hoặc *thu hẹp* Scope.
- Tuyệt đối không có khả năng *thêm* quyền hạn mà Base Profile không có.

## 3. Versioning
Mọi thay đổi trên Profile và Skill đều được quản lý bởi cơ chế `ProtectedResource` và `ProtectedResourceRevision`.
- Các bản Draft có thể sửa đổi.
- Khi Publish, bản sửa đổi trở thành Immutable.
- Metadata của Agent Run luôn tham chiếu cứng đến `revision_token` để đảm bảo có thể tái hiện chính xác phiên bản đã dùng (Reproducibility).

## 4. Bảo mật
- Tất cả các cấu hình bảo mật, secret API keys và prompt "mật" không bao giờ được gửi xuống Frontend thông qua API Preview/List.
- Backend GovernanceKernel tiếp tục là chốt chặn cuối cùng tại lớp Runtime để xác nhận tính hợp lệ của mọi hoạt động gọi Tool.
