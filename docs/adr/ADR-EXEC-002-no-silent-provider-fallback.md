# ADR-EXEC-002: Không fallback im lặng khi Execution Provider không tồn tại

## Context
Trong `AgentRuntimeManager.get_runtime()` (`app/agents/runtime/manager.py:41-50`), khi một runtime được yêu cầu nhưng không có trong registry, manager tự động fallback về `mock`.

Đối với agent text thuần (LLM generation), fallback về mock chỉ dẫn đến kết quả giả lập (placeholder response). Tuy nhiên, đối với **Execution Runtime** (chạy code trong môi trường cô lập):
- Nếu người dùng hoặc agent yêu cầu chạy trong `opensandbox` để xử lý dữ liệu thực tế, nhưng sandbox cấu hình sai / chưa khởi tạo mà hệ thống âm thầm chạy `MockExecutor`, hệ thống sẽ giả vờ hoàn thành tác vụ mà không thực thi gì cả.
- Đây là lỗi an toàn nghiêm trọng: tạo ra ảo tưởng rằng code đã được thực thi và kiểm chứng an toàn trong container cô lập, dẫn tới sai lệch dữ liệu và mất tính toàn vẹn nghiệp vụ.

## Decision
1. `ExecutionProviderManager.get(name)` **bắt buộc raise** `ExecutionRuntimeError(code=ExecutionErrorCode.EXEC_PROVIDER_UNKNOWN)` nếu provider được chỉ định không có trong registry hoặc không khả dụng.
2. Tuyệt đối không fallback ngầm về `MockExecutor` trong môi trường runtime sản xuất khi provider yêu cầu không khớp.
3. `MockExecutor` chỉ được dùng khi được chỉ định rõ ràng (`COSA_EXECUTION_PROVIDER=mock` hoặc request explicitly targeting `mock`).

## Consequences
- Bất kỳ lỗi cấu hình OpenSandbox server hoặc thiếu API key sẽ được báo lỗi rõ ràng ngay lập tức (Fail Fast).
- Đảm bảo tính minh bạch và an toàn tuyệt đối cho các tác vụ AI Workforce.
