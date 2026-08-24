# Integration: OpenTelemetry

## Trạng thái: CHƯA IMPLEMENT

Không có wiring OpenTelemetry nào trong `packages/agent_core/`, `apps/cosa/`, hay `packages/agent_integrations/` tính tới cuối phiên Wave 0-11 (2026-08-24). Không có `opentelemetry-*` package trong bất kỳ `requirements.txt`/`pyproject.toml` nào.

## Vì sao nhắc tới trong checklist

Blueprint V2 §79 liệt kê `docs/integrations/opentelemetry.md` như 1 file bắt buộc trong danh sách documentation-as-code — nhưng liệt kê 1 file doc không có nghĩa feature đã tồn tại. Ghi nhận trung thực ở đây thay vì bỏ qua file hoặc viết nội dung giả.

## Observability hiện tại (thay thế tạm)

- `RunEventRecord` (`packages/agent_core/runs/models.py`) lưu structured event trong Postgres — có thể query lịch sử run, nhưng không phải distributed tracing.
- `map_run_event_to_ag_ui()` (`packages/agent_integrations/ag_ui/event_mapper.py`, Wave 9) chuyển `RunEventRecord` sang vocabulary AG-UI cho client hiển thị — vẫn không phải OTel span/trace.
- Logging hiện tại: chuẩn Python `logging`, không có correlation ID xuyên service (Python agent_core ↔ TypeScript services/cosa) ngoài `run_id` truyền thủ công.

## Việc cần làm khi implement

1. Quyết định instrumentation boundary: span nên bọc quanh `CapabilityGateway.execute()` (mỗi tool invocation) và `ExecutionKernel.run()` (mỗi run) — 2 điểm breaking nhất để debug latency.
2. Trace context (`traceparent`) cần truyền qua network hop Python↔TypeScript (`services/cosa` control-plane client, Wave 7) — không tự phát minh header riêng, dùng W3C Trace Context chuẩn.
3. Không dùng OTel để quyết định business logic (đúng nguyên tắc CLAUDE.md #7 "trạng thái ứng dụng phải structured, không suy diễn từ văn bản tự nhiên") — OTel chỉ là observability, không thay `RunEventRecord`.
