# Workflows

> **Lưu ý:** subsystem này tồn tại từ TRƯỚC phiên làm việc Blueprint V2 (2026-08-24) — tài liệu này viết lại dựa trên audit code hiện có, không phải mô tả công việc mới trong phiên.

## 1. Mục đích

`WorkflowEngine` thực thi DAG khai báo (`WorkflowSpec`) có parallel branch, compensation (rollback khi fail), governance cho `tool_call` step, checkpoint để resume an toàn.

## 2. Khi nào sử dụng

Khi cần orchestrate nhiều bước có thứ tự/phụ thuộc rõ ràng (không phải 1 vòng lặp reasoning tự do như `ExecutionKernel`) — vd quy trình phê duyệt thanh toán nhiều bước.

## 3. Không dùng cho việc gì

Không thay thế `ExecutionKernel` cho model reasoning tự do.

## 4. Kiến trúc và luồng dữ liệu

2 chế độ: linear step pipeline (`start`/`resume`, backward-compat) và DAG khai báo (`execute_spec`/`resume_spec`, parallel + compensation + checkpoint). Dùng `GovernanceStateStore` cho `tool_call` step (ĐÃ dùng đúng từ trước — khác `CapabilityGateway` từng có state riêng, xem `ADR-DURABLE-IDENTITY.md`).

## 5. Public contracts/API

`agent.workflows.engine.WorkflowEngine`, `agent.workflows.schema.WorkflowSpec/WorkflowStepSpec`, `agent.workflows.definition_registry.WorkflowDefinitionRegistry`.

## 6. Database/schema liên quan

Chưa audit chi tiết trong phiên này — xem `packages/agent/workflows/repository.py`.

## 7-16.

Chưa audit sâu trong phiên Wave 0-11 (không nằm trong phạm vi công việc chính) — cần 1 pass tài liệu hoá riêng nếu cần chi tiết đầy đủ theo template 16 mục.
