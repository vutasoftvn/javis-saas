# Recipe: Advisor-Orchestrator-Worker

Pattern `supervisor-worker` (Blueprint V2 §70). Khác các recipe khác trong Wave 11 — recipe này **không cần code mới**, chỉ mô tả cách compose `packages/agent_core/coordination/{supervisor,parallel,quality_gate,synthesis}.py` đã tồn tại sẵn từ trước phiên làm việc này.

## Trạng thái phụ thuộc (2026-08-24)

4 module coordination đã tồn tại và có test riêng (`tests/agent_core/coordination/`, chưa audit trong phiên này). Recipe này là tài liệu hoá cách dùng chúng cùng nhau, không phải code mới.
