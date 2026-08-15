# Orchestrator Project Cycle Command Design

## Goal

Cho phép Founder tạo (hoặc nối vào) một Project rồi thiết lập MVP roadmap + OKR + chu kỳ N-tuần
qua chat hoặc voice, với N tuần tuỳ ý chứ không cố định 12/13 - đi qua đúng con đường "AI soạn
đề xuất, người bấm duyệt" đã có sẵn (`WorkOrchestratorService` + `AgentProposalService`), thay
vì bắt LLM tự do trong hội thoại bịa ra một khối JSON roadmap/OKR phức tạp.

Đây là phần tiếp nối của `docs/superpowers/specs/2026-08-15-chat-voice-n-week-execution-design.md`
(mục "Project, OKR and N-week Flow") và
`docs/superpowers/plans/2026-08-15-command-proposal-approval-foundation.md` (đã implement phần
nền: `AgentProposal` + `ProposalCommand` frozen/allowlist + apply-once). Không xây lại hạ tầng
propose/approve/execute đã có - chỉ mở rộng nó.

## Bug chặn đường - phải sửa trước

`WorkOrchestratorService.handle_command`'s nhánh high-risk (`agents/orchestrator/service.py`)
tạo `AgentProposal` với payload dạng
`{"command": {"action": ..., "category": ..., "target_resource_type": ..., "payload": {...}}}`.
Nhưng `ProposalCommand` (`agents/proposals/command.py`, `model_config = ConfigDict(extra=
"forbid")`) chỉ chấp nhận đúng
`{"command": {"command_type": "okr_objective.create"|"strategy_task.create", "idempotency_key":
..., "arguments": {...}}}`. Hai shape không khớp field name lẫn value allowlist. Đã tái hiện
trực tiếp:

```
req = OrchestratorRequest(category=PLAN_CYCLE_COMMAND, action="activate_cycle",
                           payload={"duration_weeks": 6, "title": "PMF validation cycle"})
WorkOrchestratorService.handle_command(...) → ValidationError: 7 validation errors
```

Test hiện có (`test_work_orchestrator.py::test_orchestrator_creates_proposal_for_high_risk_action`)
mock hẳn `AgentProposalService.create_proposal` nên không bao giờ chạm code thật này - bug ẩn
hoàn toàn với test suite. Mọi command PLAN_CYCLE_COMMAND đi qua orchestrator hôm nay đều crash
500 chưa bắt.

## Scope and Decisions

- **Không nới lỏng `ProposalCommand`'s allowlist strict/frozen.** Đây là biên an toàn có chủ
  đích (theo đúng tinh thần "chặn bằng cấu trúc chứ không bằng prompt"). Sửa ở phía
  `WorkOrchestratorService`: nó chịu trách nhiệm dịch `OrchestratorRequest.action`/`payload`
  sang đúng shape `command_type`/`arguments` qua một bảng ánh xạ tường minh. `action` không có
  trong bảng ánh xạ → trả về `rejected` sạch sẽ, không crash.
- **Command type mới:** `"project_cycle.setup"`, `arguments: {title, description,
  desired_week_count, existing_project_id?}`. Một proposal, một lần duyệt là xong toàn bộ chuỗi
  (đã chốt): Project → Roadmap CONFIRMED → OKR + 12WY kích hoạt thật.
- **Tái dùng nguyên vẹn** `ProjectOrchestrationService`/`RoutingService` đã có, đã test, đang
  chạy thật trong UI thủ công (`ProjectKickoffView`) - không viết lại logic sinh roadmap/OKR
  bằng tay trong `apply_proposal`. Đây là điểm khác biệt cốt lõi so với để LLM tự bịa JSON ngay
  trong hội thoại: hai bước AI-generation (roadmap, stage plan) dùng đúng prompt chuyên biệt đã
  tune sẵn, không phải general chat model tự do.
- **Cả hai điểm vào - voice và Hub Chat text** (đã chốt, biết rõ đây là phạm vi lớn hơn so với
  chỉ nối voice): `WorkIntentClassifier` hiện chỉ gắn với LiveKit tool
  (`runtime_classify_intent`, chưa ai gọi) và hoàn toàn tách rời `chat_execution_service.py`
  (Hub Chat text đi qua AI+tool loop riêng, không đụng tới orchestrator). Cả hai cần được nối
  thật trong spec này.
- **Không đổi hành vi Hub Chat cho mọi lượt khác** - chỉ chèn một bước classify rẻ (không tốn
  LLM call) ở đầu `_execute_turn`, short-circuit đúng trường hợp CYCLE_CHANGE có đủ tín hiệu;
  mọi lượt còn lại rơi thẳng vào loop AI+tool hiện có, không đổi gì.

## Architecture

### 1. Sửa `WorkOrchestratorService` - dịch action → command_type

Thêm bảng ánh xạ tường minh trong `agents/orchestrator/service.py`:

```python
_ACTION_TO_COMMAND_TYPE = {
    "activate_cycle": "project_cycle.setup",
    "setup_project_cycle": "project_cycle.setup",
}
```

Nhánh `requires_approval` build `payload["command"]` theo đúng shape `ProposalCommand` chờ đợi
(`command_type`, `idempotency_key`, `arguments`) thay vì shape tự do hiện tại. `action` không
có trong bảng → trả `OrchestratorResponse(status="rejected", message="Hành động chưa được hỗ
trợ")` thay vì để exception rơi tự do lên FastAPI.

### 2. Command mới `project_cycle.setup`

`agents/proposals/command.py::ProposalCommand.command_type` thêm literal
`"project_cycle.setup"`.

`agents/proposals/service.py::apply_proposal` thêm nhánh xử lý:

1. `existing_project_id` có giá trị → dùng project đó; không thì tạo `Project(title,
   description)` mới trong workspace.
2. `ProjectOrchestrationService(db, workspace_id, brain_id, user_id).generate_roadmap(project_id)`
   - AI soạn 2-4 stage (dùng nguyên `_ROADMAP_PROMPT` đã có).
3. `.save_roadmap_draft(project_id, draft)` → persist DRAFT `MvpStage` rows.
4. `.confirm_roadmap(project_id)` → DRAFT → CONFIRMED cho tất cả stage.
5. Lấy stage `sequence_no == 1`; `RoutingService(db, workspace_id, brain_id, user_id)
   .plan_stage(stage.id, desired_weeks=arguments["desired_week_count"])` (xem mục 3) → AI soạn
   objectives + đúng N mục weekly_focus.
6. `.activate_stage(project_id, stage.id, plan_draft)` → tạo thật `OkrCycle` + `Objective`/`KR`
   + `TwelveWeekCycle(duration_weeks=N)` + `WeeklyPlan`.

`brain_id` lấy qua `db.query(Brain).filter(Brain.workspace_id == workspace_id).first()`, cùng
pattern với `project_orchestration_router.py::_service()`.

Lỗi ở bước 2 hoặc 5 (AI trả JSON không hợp lệ - `generate_roadmap`/`plan_stage` đã tự raise
`HTTPException` 422/503) phải để `apply_proposal` propagate lỗi rõ ràng, KHÔNG để proposal rơi
vào trạng thái nửa vời (project đã tạo nhưng roadmap chưa lưu) mà vẫn báo "applied" - proposal
giữ nguyên `status="approved"` (chưa "applied"), Founder thấy lỗi và có thể thử áp dụng lại.

### 3. `RoutingService.plan_stage` nhận số tuần tuỳ chỉnh

Hiện `_PLAN_PROMPT` hardcode "ĐÚNG 12 trọng tâm tuần". Đổi chữ ký thành
`plan_stage(self, mvp_stage_id: int, desired_weeks: int = 12)`, tham số hoá câu lệnh trong
prompt (`f"ĐÚNG {desired_weeks} trọng tâm tuần"`) và JSON ví dụ tương ứng. Endpoint REST
`POST /stages/{id}:plan` hiện có giữ nguyên default 12 (không đổi hành vi UI thủ công hiện tại)
- chỉ orchestrator truyền `desired_weeks` khác 12 khi có.

### 4. Điểm vào Voice

Tool mới trong `company_runtime/tools.py`, cạnh `runtime_classify_intent`:

```python
@register("runtime", "dispatch_cycle_command", flag_key=FLAG_WORK_INTENT_CLASSIFIER_V13_1)
def runtime_dispatch_cycle_command(db, workspace_id, user_id, duration_weeks, project_hint=None, existing_project_id=None) -> dict:
```

Gọi thẳng `WorkOrchestratorService.handle_command` với
`category=PLAN_CYCLE_COMMAND, action="activate_cycle"`. LiveKit voice agent flow: nói
`confirmation_prompt` (đã có sẵn từ `runtime_classify_intent`) → chờ xác nhận bằng lời → gọi
tool này → đọc lại `message` trả về (đề xuất đã tạo, chờ duyệt).

### 5. Điểm vào Hub Chat text

`chat_execution_service.py::_execute_turn`, ngay đầu (trước khi build `chat_turns`/vào vòng lặp
AI): gọi `WorkIntentClassifier.classify(user_message.content)` (rẻ, thuần regex, không tốn AI
call). Nếu `intent == "CYCLE_CHANGE"` và trích được `duration_weeks` (luôn có, default 13) +
`project_hint` (có thể None) VÀ đây không phải one-shot session:

- Không vào vòng lặp AI+tool bình thường của lượt này.
- Tra `Project.title.ilike(f"%{project_hint}%")` trong workspace (cùng logic
  `strategy_list_projects`) để quyết định `existing_project_id`; không khớp thì để trống (proposal
  sẽ tạo project mới với `title = project_hint` hoặc một tiêu đề mặc định nếu không có hint).
- Gọi `WorkOrchestratorService.handle_command` ngay trong lượt này - **không có vòng hỏi xác
  nhận riêng bằng lời trước khi tạo proposal**, khác với nhánh voice ở mục 4. Quyết định này cố
  tình đơn giản hoá: bản thân proposal ở trạng thái "pending" CHÍNH LÀ bước xác nhận (Founder
  duyệt bằng cách bấm approve, giống hệt cách mọi proposal `okr_objective`/`strategy_task` khác
  đang hoạt động) - không cần thêm một lượt hỏi-đáp "có/không" bằng chat trước đó, vì vậy không
  cần lưu state "đang chờ xác nhận" giữa các lượt. `WorkIntentClassifier.generate_confirmation_prompt`
  chỉ được dùng cho voice (mục 4), nơi việc hỏi-đáp bằng lời trước khi hành động là UX tự nhiên hơn.
- Ghi thẳng `assistant.content` = `response.message` (case tạo proposal thành công) hoặc câu báo
  lỗi rõ ràng (case `action` không map được command_type, xem mục 1), `status="delivered"` -
  không gọi AI provider cho lượt này.

Mọi intent khác (`CHAT`, `QUICK_TASK`, `COMPANY_WORK`, `STRATEGIC`, `APPROVAL`) đi thẳng vào
vòng lặp AI+tool hiện có, không đổi gì - giữ nguyên hành vi Hub Chat cho toàn bộ hội thoại
thông thường.

## Testing

- `test_work_orchestrator.py`: bỏ mock `create_proposal` ở test hiện có (hoặc thêm test song
  song không mock) để chạy qua `_validated_payload` thật; assert action không có trong bảng ánh
  xạ trả `rejected` thay vì raise.
- `test_agent_proposal_bridge.py`: thêm case `project_cycle.setup` - happy path tạo đủ
  Project/Roadmap/OKR/12WY; case AI trả JSON hỏng ở bước roadmap/plan giữ nguyên
  `status="approved"` (không "applied"), không tạo dữ liệu nửa vời.
- `test_routing_service.py` (hoặc file tương đương hiện có cho `RoutingService`): `plan_stage`
  với `desired_weeks=6` trả đúng 6 phần tử `weekly_focus`; không truyền `desired_weeks` vẫn ra
  12 như cũ (không phá test/hành vi hiện có).
- Test mới cho tool `runtime_dispatch_cycle_command`.
- Test mới cho short-circuit trong `chat_execution_service.py`: message chứa "chu kỳ 6 tuần cho
  dự án X" tạo command CYCLE_CHANGE, không gọi `router.stream_chat` (AI provider) cho lượt đó;
  message thường (`"OKR của tôi thế nào"`) vẫn đi qua vòng lặp AI+tool như cũ.

## Out of Scope

- Đổi allowlist `ProposalCommand` để chấp nhận shape tự do hơn - cố tình giữ chặt.
- Progress reporting, Hologram Hub UX, report automation - các mục khác trong spec N-week gốc,
  để làm ở plan riêng theo đúng ghi chú tự-review của
  `2026-08-15-command-proposal-approval-foundation.md`.
- Sửa lỗi ký tự rác ("cyjHiện tại...") quan sát được trong Hub Chat - xem
  `2026-08-15-hub-chat-project-grounding-design.md`.
- Cho phép sửa/preview roadmap trước khi approve trong chat - đề xuất được apply nguyên trạng
  như AI soạn; sửa tay vẫn phải qua UI (`ProjectKickoffView`) sau khi đã activate, giống hệt
  luồng thủ công hiện tại.
