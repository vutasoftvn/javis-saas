# `apps/cosa/tests/` — phạm vi thư mục này

Thư mục này chứa test cho `apps/cosa/agents/specs.py` (AgentSpec catalog: các
role executive/specialist, `capability_refs`, `advisory_only` invariant, v.v.)
— chạy qua `make apps-cosa-test`.

**Test cho worker/governance/executive-board KHÔNG nằm ở đây** — chúng ở
top-level `tests/`, cùng cây với `tests/agent/`, `tests/e2e/`:

- Workflow governance runtime (`governed_workflow_run`, `workflow_gate`
  resume, live authority cho tool/approval step):
  `tests/apps/cosa/worker/test_governed_workflow_run.py`,
  `tests/apps/cosa/events/test_governed_workflow_trigger.py`.
- Executive Advisory Board (deliberation, role activation, evidence):
  `tests/agent/executive_board/`,
  `tests/contracts/test_executive_advisor_role_catalog.py`,
  `tests/e2e/test_executive_advisory_board*.py`.
- Founder-configurable asset (clone/publish lifecycle, cross-plane event
  consumption): `tests/agent/assets/`, `tests/apps/cosa/assets/`,
  `tests/apps/cosa/events/test_founder_asset_events.py`.

Lý do tách: `apps/cosa/tests/` chạy trong gate `apps-cosa-test` (coverage
riêng, DB isolate qua fixture nhẹ); phần lớn worker/governance/e2e test cần
hạ tầng nặng hơn (Postgres thật, disposable cluster, hoặc toàn bộ 4-plane
stack) nên sống ở `tests/` cấp root, chạy qua `make agent-test` /
`make e2e-test` / `make e2e-cross-plane-smoke` tuỳ loại. Đọc README này
trước khi audit coverage chỉ bằng cách nhìn 1 thư mục — dễ kết luận nhầm là
"thiếu test" trong khi thực ra nằm ở nơi khác.
