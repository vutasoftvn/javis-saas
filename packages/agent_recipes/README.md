# packages/agent_recipes

Corpus các workflow pattern tái sử dụng được (Blueprint V2 §70), chuẩn hoá thành `AgentSpec`/`WorkflowSpec` có thể instantiate qua `packages/agent`, thay vì copy nguyên demo application từ nguồn tham khảo bên ngoài.

## Cấu trúc mỗi recipe

```text
agent_recipes/<domain>/<recipe-id>/
├── recipe.yaml   # metadata + workflow (pattern + steps, có deterministic_boundary khi cần)
│                 # + requires (capabilities/skills/modules — tham chiếu, không copy nội dung)
│                 # + outputs + governance
└── README.md     # trạng thái phụ thuộc thật, cách instantiate
```

Đã hiệu chỉnh so với thiết kế Wave 0.2 ban đầu (bỏ `workflow.yaml`/`agents/`/`skills/`/`evals/` riêng —
1 file `recipe.yaml` đủ diễn đạt, tránh nhiều file rỗng/trùng lặp cho 7 recipe đầu tiên; tách thêm
file khi 1 recipe thực sự cần nhiều agent/skill phức tạp hơn).

## Quy tắc bắt buộc

1. Recipe **không có authority riêng** — chỉ tham chiếu `CapabilitySpec`/`SkillSpec`/`WorkflowSpec` public đã publish, không tự định nghĩa authorization mới.
2. Không hard-code 1 pattern vào 1 SDK cụ thể — mỗi runtime adapter (`packages/agent_integrations/*`) tự map pattern sang primitive phù hợp, qua conformance test.
3. Skill/eval mà recipe cần phải đã tồn tại ở `skillpacks/` / `evals/` (xem A10-A11 trong `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md`) — không tạo bản sao skill riêng cho từng recipe.

## Trạng thái hiện tại (2026-08-24)

7 recipe ưu tiên theo Blueprint V2 §81 Wave 11 đã tạo (`recipe.yaml` + `README.md`), tài liệu tương ứng ở `docs/recipes/`:

- `sales/competitor-intelligence`, `research/research-synthesize` — cần `web.search` capability (chưa implement).
- `ops/release-radar` — dùng control-plane Wave 7 (chưa verify Postgres/Encore thật).
- `core/advisor-orchestrator-worker`, `core/mixture-of-agents` — dùng `coordination/*` đã có sẵn từ trước.
- `dev/dependency-doctor` — cần `web.search` + nguồn CVE database (chưa quyết định).
- `core/self-improving-skill` — dùng `skills/lab/` Wave 5-6, đã có test pass.

Toàn bộ recipe ở đây là **spec khai báo** (declarative), không có runtime code riêng — instantiate qua compose `AgentSpec`/`WorkflowSpec` với capability/skill/module đã tham chiếu.
