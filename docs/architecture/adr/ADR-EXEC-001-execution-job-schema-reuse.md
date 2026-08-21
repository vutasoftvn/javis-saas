# ADR-EXEC-001: Execution Job Schema — tạo mới hai bảng, dùng lại phần còn lại

## Context
Spec `COSA_OpenSandbox_Agent_Runtime_Integration_v13.1_v13.2.md` §25 đề xuất bốn bảng mới:
`execution_jobs`, `execution_steps`, `execution_artifacts`, `execution_audit`.

Codebase đã có hai thứ trùng ngữ nghĩa:
- `artifacts` (`app/modules/outcomes/models.py`) có sẵn `workspace_id`, `object_storage_uri`,
  `content_hash`, `status`, và cả `run_id` lẫn `outcome_id` đều nullable.
- `agent_events` + `agent_tool_calls` (`app/agents/governance/models.py`) đã là audit trail
  của Agent Runtime, có `AuditLog` (`app/core/audit.py`) ở tầng nền.

Copy nguyên văn §25 sẽ tạo ra ba kho artifact và ba kho audit song song trong cùng một
database.

## Decision
1. **Tạo mới** `execution_jobs` và `execution_steps`. `outcome_runs`/`run_steps` là cấp
   nghiệp vụ (`depends_on_step_ids`, `expected_output`), không diễn tả được "một câu lệnh +
   exit_code"; `developer_jobs` thuộc Local Worker Plane của desktop.
2. **Không tạo** `execution_artifacts`. Thêm cột nullable `execution_job_id` vào `artifacts`.
3. **Không tạo** `execution_audit`. Ghi vào `agent_events`; `execution_jobs.agent_run_id`
   (nullable FK `agent_runs.id`) nối job hạ tầng với run nghiệp vụ.
4. **Tạo mới** `sandbox_policies` (§26), seed 5 preset của §48 ở scope global.

## Consequences
- Một job sandbox không bắt buộc phải có `Outcome` — `artifacts.outcome_id` vẫn nullable.
- Câu hỏi "agent này đã làm gì" trả lời được bằng một nguồn (`agent_events`), không phải hợp
  nhất hai bảng.
- Migration chạm đúng một bảng business hiện có, bằng một cột nullable — vẫn additive-only.
</content>
