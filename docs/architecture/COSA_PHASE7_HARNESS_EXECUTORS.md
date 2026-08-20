# COSA Phase 7: Harness and Executor Integration

Tài liệu này trình bày chi tiết về kiến trúc đóng gói (wrapper) và quản trị (governance) đối với các LLM/Runtime providers bên ngoài như DeepSeek Harness, Codex, Claude Code, và n8n.

## 1. Governance Boundary
COSA Core **không bao giờ** import hoặc chạy trực tiếp mã nguồn của vendor. Mọi vendor SDK/API đều phải được bọc trong một Adapter triển khai theo chuẩn `RuntimeAdapter` hoặc `ExecutorProvider`. Các Adapter này phải nằm trong hệ thống module `app/workforce/adapters/`.

## 2. Các chế độ của DeepSeek Harness (DSH)
DeepSeek Harness có hai chế độ hoạt động chính:
- **`cosa_governed`**: Agent chạy với đặc quyền của hệ thống COSA. Chế độ này bị chặn toàn bộ các native tools của DSH, thay vào đó mọi lời gọi công cụ (tool calls) từ mô hình phải đi qua `ToolInvocationService` của COSA (áp dụng đầy đủ chính sách Approval, RBAC, và Event Emission).
- **`isolated_coding`**: Chế độ Sandbox thuần túy. Agent được cung cấp OpenSandbox (cô lập về mạng và filesystem). Agent không thể gọi các tool production của COSA và không có quyền truy cập vào Credentials hay Secret Broker.

## 3. Mã Hóa Coding Executor (Codex & Claude Code)
Codex và Claude Code được cấu hình mặc định là các Executor Provider và bị cưỡng bức chạy trong chế độ `isolated_coding` (chỉ được cung cấp OpenSandbox). Bất kỳ nỗ lực nào lấy credential sẽ bị chặn.

## 4. Quản trị Callback n8n
N8n hoạt động như một hệ thống xử lý bất đồng bộ, webhook-based. COSA giới hạn n8n không được cập nhật trực tiếp Workflow State. Kết quả từ n8n phải được trả về qua callback có chữ ký bảo mật kèm theo `correlation_id` do COSA sinh ra lúc gọi. COSA sau đó dùng thông tin này để cập nhật state.

## 5. UI và Giám sát
Chế độ chạy (Governed hay Isolated) và Tên của Provider đang xử lý Node được phát qua `NodeStartedEvent` và lưu vào Projection. Giao diện (Flutter Hologram UI) sẽ hiển thị biểu tượng bảo vệ để người vận hành (operator) có thể dễ dàng phân biệt agent đang chạy ở mức an toàn nào.
