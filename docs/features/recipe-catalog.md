# Recipe Catalog

## 1. Mục đích

Chuẩn hoá workflow pattern tái sử dụng được (`packages/agent_recipes/<domain>/<recipe-id>/`) thành `recipe.yaml` khai báo — không copy nguyên demo application từ nguồn tham khảo bên ngoài.

## 2. Khi nào sử dụng

Khi cần 1 pattern đã được đặt tên/mô tả rõ (research-synthesize, watch-rank-deliver, supervisor-worker, critic-revise, mixture-of-agents, self-improving-skill) thay vì thiết kế lại từ đầu.

## 3. Không dùng cho việc gì

Recipe KHÔNG có authority riêng — chỉ tham chiếu `CapabilitySpec`/`SkillSpec`/module đã publish/tồn tại, không tự định nghĩa authorization mới.

## 4. Kiến trúc và luồng dữ liệu

```
agent_recipes/<domain>/<recipe-id>/
├── recipe.yaml   # metadata + workflow (pattern + steps + deterministic_boundary) + requires + governance
└── README.md     # trạng thái phụ thuộc thật
```

7 recipe hiện có (Wave 11): `sales/competitor-intelligence`, `research/research-synthesize`, `ops/release-radar`, `core/advisor-orchestrator-worker`, `dev/dependency-doctor`, `core/self-improving-skill`, `core/mixture-of-agents`.

## 5. Public contracts/API

Không có Python API riêng — recipe là spec khai báo, instantiate thủ công qua compose `AgentSpec`/`WorkflowSpec` với `capability_refs`/`pinned_skills` tham chiếu trong `recipe.yaml`.

## 6. Database/schema liên quan

Không có.

## 7-8.

Xem từng `docs/recipes/<recipe-id>.md` cho chi tiết governance/dependency status của từng recipe.

## 9. Cách bổ sung recipe mới

Tạo `packages/agent_recipes/<domain>/<recipe-id>/{recipe.yaml,README.md}` + `docs/recipes/<recipe-id>.md`, thêm entry vào `docs/manifest.yaml` (`recipes:` section). Đặt `workflow.pattern` theo 1 trong 12 pattern canonical (Blueprint V2 §70): single-agent, router, sequential, parallel, map-reduce, supervisor-worker, critic-revise, debate, mixture-of-agents, research-synthesize, watch-rank-deliver, human-approval-resume.

## 10-16.

3/7 recipe (`advisor-orchestrator-worker`, `self-improving-skill`, `mixture-of-agents`) tái dùng module Python đã có sẵn/xây trong phiên này, không cần code mới. 4/7 recipe còn lại cần `web.search` capability (chưa implement) hoặc control-plane Wave 7 (chưa verify) trước khi chạy end-to-end được — xem `packages/agent_recipes/README.md` để biết trạng thái từng recipe.
