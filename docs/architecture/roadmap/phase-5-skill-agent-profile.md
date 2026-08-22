# Phase 5 — Skill System & Agent Profile

> Chi tiết thực thi cho Phase 5 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Skillpacks hiện có (`skillpacks/okr`, `skillpacks/tasks`, `skillpacks/core/weekly-review`, `skillpacks/marketing/*` x5) đã compliant với §11.1-11.3 (manifest.yaml + SKILL.md đúng schema) — phần việc ở đây là formalize registry/router, không viết lại skillpacks hiện có.

## 5a. Skill Registry & Manifest Enforcement (§11.2-11.3)

**Task:**
1. Định nghĩa schema manifest chuẩn (Pydantic) tại `agentos/skills/manifest_schema.py`, dựa đúng field đã thấy trong `skillpacks/okr/manifest.yaml` hiện có: `apiVersion, kind, metadata{id,name,version,description}, publisher{name,type}, source{type,path}, capability{domain,category,intents}, runtime{environment,entrypoint}, permissions{required}, risk{level}, trust{tier}`.
2. Viết loader `agentos/skills/registry.py::SkillRegistry` — quét toàn bộ `skillpacks/**/manifest.yaml` khi khởi động, validate qua schema Pydantic, reject skill nào thiếu field bắt buộc (fail loudly khi khởi động, không silently skip skill lỗi).
3. Wire `SkillRegistry` vào `build_cosa_agent_plane()` (Phase 0b) — hiện composition root đã có tham số `skill_router`/`skill_instruction_loader`, đảm bảo chúng thực sự đọc từ `SkillRegistry` mới này thay vì stub.
4. Viết router logic tối thiểu: nhận intent text (câu hỏi/yêu cầu của user) → so khớp với `capability.intents` của từng skill (bắt đầu bằng keyword/embedding similarity đơn giản, không cần model phức tạp ở MVP) → trả về danh sách skill candidate xếp hạng.
5. Trước khi router chọn 1 skill để thực thi, kiểm tra `permissions.required` của skill có nằm trong quyền hiện tại của agent/role không (dùng `evaluate_access()` từ Phase 1c) — nếu thiếu quyền, skill bị đánh dấu "unavailable", agent phải giải thích cho user thay vì cố chạy.

**Acceptance:**
- [ ] `SkillRegistry` load thành công toàn bộ skillpacks hiện có (`okr, tasks, core/weekly-review, marketing/*` x5) không lỗi.
- [ ] Test: manifest thiếu field bắt buộc → registry raise lỗi rõ ràng khi khởi động (không phải lỗi mơ hồ hoặc bị bỏ qua âm thầm).
- [ ] Test router: intent đúng → skill đúng được chọn hạng 1; intent gần nhưng không phù hợp → skill đó không lọt top candidate.
- [ ] Test: skill thiếu tool permission → bị đánh dấu unavailable, không thực thi, agent có thông điệp giải thích thay vì lỗi crash hoặc hallucinate kết quả.
- [ ] `build_cosa_agent_plane()` dùng `SkillRegistry` thật, không còn stub.

## 5b. Strategy Skills (§5.2, gắn với Phase 2 tool)

**Bối cảnh:** phụ thuộc trực tiếp entity/service đã tạo ở Phase 2 (`assumptions, experiments, evidence, gate_evaluations, decision_records, next_action_candidates/rankings`) — chỉ bắt đầu khi Phase 2 đã có API handler thật để tool gọi vào.

**Task — tạo 7 skillpack mới dưới `skillpacks/strategy/<name>/`, mỗi skill có `manifest.yaml` + `SKILL.md` theo đúng template đã dùng cho `skillpacks/okr`:**

1. `strategy.stage-assessment` — intents: "đánh giá giai đoạn startup", "xác định stage hiện tại". Tool dependency: `strategy.project.get`, `strategy.gate_evaluation.list`.
2. `strategy.assumption-discovery` — intents: "tìm giả định chính", "xác định rủi ro chưa kiểm chứng". Tool: `strategy.assumption.create`, `strategy.assumption.list`.
3. `strategy.experiment-design` — intents: "thiết kế thử nghiệm", "đề xuất cách kiểm chứng giả định". Tool: `strategy.experiment.create`.
4. `strategy.evidence-synthesis` — intents: "tổng hợp bằng chứng", "đánh giá độ mạnh evidence". Tool: `strategy.evidence.create`, `strategy.evidence.list`.
5. `strategy.gate-evaluation` — intents: "đánh giá gate", "có đủ điều kiện qua stage tiếp theo không". Tool: `strategy.gate_evaluation.create`.
6. `strategy.decision-capture` — intents: "ghi nhận quyết định", "chốt hướng đi". Tool: `strategy.decision_record.create`.
7. `strategy.next-best-action` — intents: "việc gì nên làm tiếp theo", "ưu tiên tuần này". Tool: `strategy.next_best_action.get` (endpoint `GET /operations/strategy/projects/:id/next-best-actions` từ Phase 2d).

**Mỗi `SKILL.md` bắt buộc có đủ 10 mục theo §11.2 guide gốc:** mục tiêu; khi nào dùng/không dùng; prerequisites; deterministic steps; tool calls được phép; approval points; output format; failure/edge case; examples; evidence requirements.

**Ràng buộc cứng phải ghi rõ trong từng `SKILL.md` liên quan tới NBA/gate:** skill **không được tự đặt priority/pass-fail bằng suy luận LLM tự do** — phải gọi tool tương ứng (đã có business logic tất định từ Phase 2c) rồi chỉ diễn giải/tóm tắt kết quả. Đây là invariant §5.2 của guide gốc.

**Task tiếp:**
8. Định nghĩa eval case cho mỗi skill: input mẫu → expected skill được chọn → expected tool call sequence → success criteria. Lưu trong `agentos/evals/strategy/` (hoặc vị trí eval hiện có trong `agentos/evals/`).

**Acceptance:**
- [ ] 7 skillpack mới tồn tại, load được qua `SkillRegistry` (5a).
- [ ] Integration test: "Founder mô tả venture mới" → router chọn đúng `strategy.stage-assessment` trước tiên.
- [ ] Test xác nhận không skill nào tự sinh next-best-action candidate bằng LLM tự do — luôn phải qua tool `strategy.next_best_action.get`.
- [ ] Eval case tồn tại cho cả 7 skill, chạy được qua eval runner hiện có của `agentos/evals/`.

## 5c. Agent Profile Schema & Registry (§12.2-12.3)

**Task:**
1. Định nghĩa Pydantic schema `AgentProfile` tại `agentos/profiles/schema.py`:
```python
class AgentProfile(BaseModel):
    id: str
    name: str
    version: str
    mission: str
    skills: list[str]              # skill id, phải tồn tại trong SkillRegistry
    tools_allow: list[str]         # tool name, phải tồn tại trong ToolRegistry
    permission_level: PermissionLevel
    preferred_runtime: Literal["native", "deepseek_harness", "adk"]
    fallback_runtime: Literal["native", "deepseek_harness", "adk"]
    max_tool_calls: int
    max_cost_usd: float
    max_runtime_seconds: int
```
2. Tạo thư mục `agentos/profiles/definitions/` chứa file YAML cho từng profile — bắt đầu tối thiểu với 1 profile "Co-Founder" (mặc định khi user không chọn agent cụ thể trong Chat, Phase 4a) và 1 profile ví dụ khác (ví dụ `sales.researcher` theo đúng mẫu §12.2 guide gốc) để chứng minh cơ chế hoạt động — **không** tạo hàng loạt profile nghiệp vụ thật ở bước này, danh sách profile thật là quyết định nghiệp vụ của người vận hành.
3. Loader validate: mọi `skills` id phải tồn tại trong `SkillRegistry` (5a), mọi `tools_allow` phải tồn tại trong `ToolRegistry` — reject profile tham chiếu skill/tool không tồn tại khi khởi động.
4. `POST /agent/conversations` (Phase 4a) nhận tham số optional `agent_profile_id` — nếu không truyền, dùng profile "Co-Founder" mặc định.
5. Khi agent trong 1 profile được "hire" thành nhân sự thật của 1 company (WorkforceMember, Phase 1b), lưu `agent_profile_id` như 1 field/metadata trên `WorkforceMember` tương ứng (không tạo bảng ánh xạ mới — mở rộng field trên bảng `identityWorkforceMembers` đã có nếu cần).

**Acceptance:**
- [ ] `AgentProfile` schema + loader hoạt động, reject profile tham chiếu skill/tool không tồn tại.
- [ ] Test: `POST /agent/conversations` không truyền `agent_profile_id` → dùng đúng profile mặc định.
- [ ] Test: `permission_level` và `preferred_runtime` của profile được `AgentRuntime`/`Executor` tôn trọng khi chạy (không bị override ngầm).
- [ ] 1 WorkforceMember AI thật có thể được gán 1 `agent_profile_id` và test lấy lại đúng.

## Dependency

5a độc lập, chỉ cần Phase 0b (composition root) xong. 5b phụ thuộc Phase 2 (Strategy domain có API/tool thật) và 5a (registry để load skill mới). 5c phụ thuộc 5a (validate skill reference) và Phase 0b (ToolRegistry để validate tool reference); tích hợp với `/agent/conversations` phụ thuộc Phase 4a đã có route đó.
