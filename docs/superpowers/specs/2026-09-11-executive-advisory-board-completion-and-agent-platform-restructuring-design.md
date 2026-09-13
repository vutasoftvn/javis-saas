# Thiết kế: Hoàn thiện Executive Advisory Board (13 role) + Tái cấu trúc Multi-agent / Tự học / Phê duyệt nâng cấp

**Ngày:** 2026-09-11
**Trạng thái:** Proposed — chờ review
**Liên quan:** `ADR-EXECUTIVE-BOARD-001-governed-project-advisory.md`,
`ADR-AGENT-REG-001-seed-agents-for-launch.md`,
`docs/superpowers/specs/2026-09-11-executive-advisory-board-design.md`,
`docs/superpowers/specs/2026-09-11-startup-default-context-and-workforce-design.md`

## Bối cảnh

COSA là nền tảng AI agent cho startup — đồng hành từ phân tích đến scale, tự động hoá — xoay
quanh 2 thực thể lifecycle chính: Workspace (W0_IDEA→W5_SCALE) và Project
(P0_DISCOVERY→P6_SCALE_GOVERN). Tài liệu này chốt lại hướng tái cấu trúc cho 2 mảng, sau khi
đối chiếu trực tiếp với code hiện có (không dựa vào tài liệu `.md`/ADR cũ cho phần khảo sát sự
thật) và tham khảo có chọn lọc 3 plugin bên
`github.com/alirezarezvani/claude-skills` (`compliance-os`, `c-level-advisor`, `c-level-agents`
/founder mode):

1. **Hoàn thiện đủ 13 role Executive Advisory Board** — hiện chỉ 2/13 role (`cfo`, `cmo`) thực
   sự `READY` end-to-end; các role còn lại bị khoá bởi phụ thuộc functional-profile chưa sẵn
   sàng, không phải vì thiếu nội dung skillpack.
2. **Tái cấu trúc lớp multi-agent / tự học / phê duyệt nâng cấp** — mục tiêu: agent phối hợp
   đa-agent thật (không chỉ Executive Board), agent có khả năng tự học từ feedback, tự đề xuất
   cải tiến, và mọi nâng cấp phải qua phê duyệt của con người.

Người dùng đã xác nhận: được phép phá vỡ/hợp nhất kiến trúc hiện tại ở Phần B nếu cần, miễn là
tận dụng tối đa những gì đã xây (không phát minh lại từ đầu những gì đã có).

## Phát hiện nền tảng (code-verified)

### 1. Executive Advisory Board — vì sao chỉ 2/13 role sẵn sàng

`ADR-EXECUTIVE-BOARD-001` (ACCEPTED 2026-09-11) ghi nhận: bản thử nghiệm trước từng để advisory
context ở mức toàn Workspace và gặp lỗi cross-project data leakage — vì vậy Executive Board
hiện tại **cố ý** Project-scoped: mọi bảng liên quan
(`project_executive_board_settings`, `project_executive_role_activations`,
`project_executive_deliberations`, `project_executive_deliberation_frames/decisions/analyses`)
đều khoá theo cặp `(workspace_id, project_id)`.

Mỗi role trong catalog 13 role (`shared/contracts/executive-advisor-roles.json`, sinh đa ngôn
ngữ TS/Python/Dart) đã có sẵn tên spec + skill pin riêng
(`cosa.executive.<role>`, `skillpack:executive/<role>-advisor@1.0.0>`) — thiết kế đã chốt:
**1 role = 1 AgentSpec + 1 skillpack riêng, code-owned**, đúng pattern
`cfo-advisor`/`cmo-advisor`/`coo-advisor` đã có trên đĩa `skillpacks/executive/`.

Mỗi role còn bị khoá bởi `required_profile_key` — chỉ chuyển `READY` khi functional profile
tương ứng (`STARTUP_TEAM_PROFILES`) `READY`:

| Role | required_profile_key | Trạng thái profile thật |
|---|---|---|
| cfo, cmo | finance, marketing | READY → role READY |
| coo, chief_of_staff | `"operations"` | READY — `operations` là `OwnerAgentProfile` độc lập, bổ sung vào `STARTUP_TEAM_PROFILES` (xem Quyết định operations 2026-09-12) |
| cco | customer_support | `PENDING_PROJECT_KNOWLEDGE` (AgentSpec `customer_support`/`customer_support_autopilot` đã deploy thật, chỉ thiếu wiring knowledge) |
| cro | sales | `PENDING_CRM_FOUNDATION` (đã có placeholder profile, chưa xong) |
| vpe | coding | `DEFERRED_CODING` (chưa có sandboxed executor thật) |
| cpo, chro, ciso, gc, cdo, caio | product, people, security, legal, data, ai_governance | **Không tồn tại trong `STARTUP_TEAM_PROFILES`** — chưa có gì cả |

Kết luận quan trọng: **việc "thiếu 9 role" không phải bài toán viết thêm 9 skillpack** — đó là
phần dễ. Bài toán thật là 7-9 functional profile nền (sales, coding, product, people, security,
legal, data, ai_governance, + làm rõ operations) chưa tồn tại hoặc chưa hoàn thiện.

### 2. Multi-agent / tự học / phê duyệt — đã xây gần đủ, chưa nối

Qua khảo sát trực tiếp `packages/agent/coordination/`, `packages/agent/skills/`,
`packages/agent/evals/`, `packages/agent/workflows/`, `packages/agent/capabilities/
approval_service.py`:

| Khối cần | Đã tồn tại ở đâu | Trạng thái thật |
|---|---|---|
| Multi-agent song song | `packages/agent/workflows/steps.py::ParallelStep/AgentStep/ParallelBranch` (chạy nhiều AgentSpec đồng thời qua `WorkflowEngine`, đang live) | Viết xong, test xong, **0 caller trong `apps/cosa`** |
| Multi-agent kiểu supervisor/specialist | `packages/agent/coordination/{supervisor,delegate,quality_gate,risk_classification,synthesis}.py` | Viết xong, test xong, **0 caller trong `apps/cosa`** — trùng chức năng với `WorkflowEngine` |
| Agent tự cải tiến skill | `packages/agent/skills/lab/lab.py::SkillOptimizationLab` (Executor→Scorer→Mutator→Challenger, tự chối auto-publish) | Viết xong, test xong, **0 caller trong `apps/cosa`** |
| Agent tự đề xuất (self-propose) | `POST /candidates` đã có field `created_by_agent` trong schema | Field tồn tại nhưng **không nơi nào trong worker điền/gọi nó** — hiện chỉ gọi được từ ngoài (người/API) |
| Feedback → học | `POST /{id}/feedback` tính `aggregate_score` | Tính xong nhưng **thuần thông tin, không ai tiêu thụ để quyết định gì** |
| Phê duyệt nâng cấp | `DurableApprovalService.create_approval_request/submit_decision` (generic, đang live trong `apps/cosa/composition/agent_plane.py`) | `verify_and_prepare_resume` **chỉ hiểu tool-call execution** (đòi `RunToolCallRecord`/`RunCheckpointRecord`/`ExecutionTargetSnapshot`) — skill-promotion phải tự chế cơ chế duyệt riêng (`approved_by`/`approval_reason`), không dùng chung |

Duy nhất Executive Board là pattern multi-agent THẬT SỰ đang chạy (mỗi advisor chạy cô lập,
không thấy draft của nhau, rồi synthesis). Mọi cơ chế tổng quát hơn đã được viết đầy đủ, test
kỹ, nhưng bị bỏ dở giữa chừng — không nối vào route/worker nào.

### 3. Nguồn nội dung tham khảo từ claude-skills cho 9 skillpack còn thiếu

`c-level-advisor/skills/` bên `github.com/alirezarezvani/claude-skills` có bản tương ứng đầy
đủ cho cả 9 role: `cro-advisor`, `cpo-advisor`, `chief-customer-officer-advisor` (cco),
`chro-advisor`, `ciso-advisor`, `general-counsel-advisor` (gc), `chief-data-officer-advisor`
(cdo), `chief-ai-officer-advisor` (caio), `vpe-advisor` — mỗi cái có
`SKILL.md + references/ + scripts/`.

**Áp dụng được (nội dung, không phải kiến trúc):**
- Bảng "Core Responsibilities" + benchmark/metrics/red-flags (NRR, Magic Number, CAC payback
  bên `cro-advisor`; liquidation preference, anti-dilution bên `general-counsel-advisor`) — đưa
  công thức/ngưỡng trực tiếp vào nội dung `SKILL.md` để model áp dụng khi tư vấn.
- "Diagnostic/Key Questions trước khi advise" — khớp đúng autonomy `L1_PROPOSE` (hỏi/đề xuất,
  không tự quyết) mà mọi role Executive Board của COSA đã bị khoá cứng.
- Bảng "Integration with Other C-Suite Roles" — tư liệu cho phần `chief_of_staff` routing/
  synthesis trong deliberation của COSA.
- Câu caveat cẩn trọng (không phải tư vấn pháp lý/không thay thế luật sư/kiểm toán viên) — giữ
  tinh thần này cho `gc-advisor`/`ciso-advisor` của COSA.

**Không áp dụng:**
- Các Python script độc lập (`revenue_forecast_model.py`, `contract_risk_scanner.py`...) làm
  `runtime.tools` — mẫu skill COSA đã đọc (`cfo-advisor`, `risk-register`) đều `tools: []`, dựa
  model tự suy luận, không gọi script ngoài. Nếu cần chạy tính toán thật, phải đăng ký
  `CapabilitySpec` mới qua `CapabilityRegistry` (đúng pipeline fail-closed hiện có validate
  `runtime.tools` tại skillpack-seed time), không đưa script rời vào skillpack.
- Mô hình workspace-wide/company-wide, stateless, không hash-pin của `c-level-advisor` —
  KHÔNG copy nguyên; COSA giữ nguyên Project-scoped + hash-pinned + advisory_l1 ceiling.
- Mô hình spawn sub-agent tự do kiểu Hermes Agent (không catalog cố định, không governance) —
  mâu thuẫn trực tiếp với `PinnedSkillRef` hash-pin và CLAUDE.md rule 5 (governance là code,
  không phải LLM tự quyết).

## Kiến trúc đề xuất

### Phần A — Hoàn thiện 13 role Executive Advisory Board

Thứ tự triển khai theo dependency thật (không phải đếm skill):

1. **cco** (ưu tiên 1, gần khả thi nhất): viết `skillpacks/executive/cco-advisor/{manifest.yaml,
   SKILL.md}` theo khuôn `cfo-advisor`; đăng ký `cosa.executive.cco`; xử lý phần wiring
   knowledge để đưa `customer_support` profile từ `PENDING_PROJECT_KNOWLEDGE` lên `READY`.
2. **cro, vpe** (ưu tiên 2): hoàn thiện functional profile `sales` (`PENDING_CRM_FOUNDATION`)
   và `coding` (`DEFERRED_CODING` — cần sandboxed executor thật, việc lớn) trước khi role
   tương ứng dùng được; viết skillpack có thể làm song song.
3. ### Quyết định operations (2026-09-12)

   `operations` là `OwnerAgentProfile` độc lập, đã có `cosa.agents.operations` và
   hash-pinned workforce identity. Nó thiếu duy nhất khỏi `STARTUP_TEAM_PROFILES`.
   `founder_assistant` chỉ là alias chat; Company cấm nó trở thành operating assignment,
   nên không được dùng làm fallback cho COO/Chief of Staff.

   Thêm `operations` làm Startup Team profile `TEMPLATE`/`READY`, data-backfill Project
   cũ, rồi đưa `chief_of_staff` và `coo` lên `READY`. Không tạo AgentSpec, skillpack,
   route hoặc auto-activation mới. Profile activation chỉ mở eligibility; Founder vẫn
   phải kích hoạt role/preset tường minh.
4. **cpo, chro, ciso, gc, cdo, caio** (ưu tiên 4, tốn công nhất): mỗi role cần 1 functional-agent
   profile mới hoàn toàn (AgentSpec, capability, entry `STARTUP_TEAM_PROFILES`, allowlist
   route-policy) trước khi skillpack advisor có ý nghĩa. Tách sub-plan riêng theo domain, làm
   sau khi Phần B ổn định (để các role mới tận dụng ngay pipeline multi-agent/approval mới,
   không dùng lại pattern cũ).

File cốt lõi: `shared/contracts/executive-advisor-roles.json` (sửa nguồn, chạy lại generator),
`skillpacks/executive/<role>-advisor/{manifest.yaml,SKILL.md}` (9 bộ mới),
`services/company/shared/contracts/startup-team-profiles.generated.ts` (nguồn generate),
`services/company/operations/services/executive-role-activation.service.ts`.

### Phần B — Tái cấu trúc multi-agent / tự học / phê duyệt

### Quyết định thực thi B.1 + B.3 (2026-09-12)

WorkflowEngine là đường orchestration workflow duy nhất. Chỉ xoá primitive không
có production caller: approval_gate.py, delegate.py, parallel.py, quality_gate.py,
risk_classification.py, supervisor.py và synthesis.py. Giữ scheduler.py,
control_plane_scheduler_client.py, delegation_envelope.py, durable_supervisor.py,
expansion.py và wait_resolver.py.

B.1 chỉ wire worker vào CosaAgentPlane.workflow_orchestration; không mở endpoint
spawn agent, prompt tự do hay role tự chọn. B.3 dùng một ledger approval cho
TOOL_CALL và CHANGE_REQUEST. Promotion workspace_custom bind candidate ID + exact
definition hash, Founder quyết định, worker recheck trước publish.

### Quyết định thực thi B.2 + B.4 (2026-09-12)

Không chạy `SkillOptimizationLab.optimize()` trực tiếp sau mọi Run và không để
worker POST qua endpoint công khai `/agent/skills/candidates`. Kernel chỉ append
observation cho từng `PinnedSkillRef` sau khi RunRecord tồn tại. Feedback được
lưu idempotent, tính aggregate theo cửa sổ và tách hoàn toàn khỏi `eval_score`.
Chỉ aggregate suy giảm qua policy server-owned mới atomically tạo improvement
request + outbox.

Worker xử lý request runless với claim fencing, reload đúng `(skill_id, version,
definition_hash)`, policy hash và evaluator suite hash. Chỉ skill trong
allow-list có evaluator đăng ký, fixture synthetic/redacted, capability-empty
eval AgentSpec và mutation budget mới đủ điều kiện. Candidate giữ lineage an
toàn và không tự publish, auto-pin, đổi capability/autonomy hay kích hoạt role.
Promotion vẫn là `CHANGE_REQUEST` Founder-reviewed của B.3. Mặc định runtime
`OFF`; `OBSERVE` không gọi model; `CANDIDATE` chỉ là cấu hình deploy có chủ đích.

**1. Hợp nhất lớp multi-agent orchestration.** Xoá
`packages/agent/coordination/{supervisor,delegate,parallel,quality_gate,risk_classification,synthesis,
approval_gate}.py` (0 caller, trùng chức năng `WorkflowEngine`/`DurableApprovalService`),
giữ `scheduler.py`, `control_plane_scheduler_client.py` (đang live). Chọn
`WorkflowEngine` + `ParallelStep`/`AgentStep`/`ParallelBranch` làm con đường multi-agent DUY
NHẤT, wire vào `apps/cosa/composition/workflow_orchestration.py`.

**2. Nối vòng tự học/tự đề xuất cải tiến có kiểm soát.** Tín hiệu suy giảm từ feedback sau khi qua
policy server-owned sẽ tạo request và outbox cải tiến bền vững; worker xử lý runless trong sandbox
cách ly và chỉ đề xuất candidate nếu vượt qua bộ kiểm thử hash-pinned.

**3. Hợp nhất cơ chế phê duyệt.** Thay cơ chế duyệt tự chế của `POST /{id}/promote` bằng
`DurableApprovalService.create_approval_request(action="promote_skill_candidate", ...)`; mở
rộng `verify_and_prepare_resume` (hoặc thêm hàm chị em) để xử lý đề xuất không phải tool-call —
có 1 sổ phê duyệt/audit trail duy nhất cho mọi loại nâng cấp cần người duyệt.

**4. Feedback → tín hiệu học thật.** Dùng aggregate feedback theo cửa sổ giảm dần làm tín hiệu
kích hoạt đề xuất cải tiến có kiểm soát qua policy, thay vì là con số nằm im hay ghi đè eval_score.

File cốt lõi: xoá `packages/agent/coordination/{supervisor,delegate,parallel,quality_gate,
risk_classification,synthesis,approval_gate}.py` + test tương ứng; giữ `scheduler.py`; sửa
`apps/cosa/composition/workflow_orchestration.py`, `apps/cosa/worker/*.py`,
`apps/cosa/api/skill_registry_routes.py`, `packages/agent/capabilities/approval_service.py`,
`packages/agent/skills/candidate_store.py`.

## Việc không nên làm

- Không auto-activate toàn bộ 13 role Executive Board ngay khi tạo workspace/project — vi phạm
  chính bài học `ADR-EXECUTIVE-BOARD-001` (workspace monolith từng gây leakage) và CLAUDE.md
  rule 3. Kích hoạt luôn phải là hành động tường minh của founder.
- Không copy mô hình Hermes Agent (spawn sub-agent tự do, không hash-pin, không catalog cố
  định) — phá vỡ `PinnedSkillRef` hash-pin và CLAUDE.md rule 5/7.
- Không dùng flow `agent_skill_candidates` (workspace_custom self-serve) để dựng phần lõi 13
  role — flow này chặn tường minh scope `platform_builtin` và không tham gia pipeline
  `contracts-check`/`skillpacks-validate` đa ngôn ngữ.
- Không port nguyên Python script phân tích từ claude-skills làm `runtime.tools`.

## Thứ tự thực hiện tổng thể

1. Phần A nhóm 1 (cco) + điều tra "operations".
2. Phần B mục 1 + 3 (hợp nhất multi-agent + approval — nền tảng cho các bước sau).
3. Phần B mục 2 + 4 (vòng tự học).
4. Phần A nhóm 2-4 (các role còn lại, làm sau khi nền tảng Phần B ổn định).

## Kiểm chứng (verification)

- Phần A: `make contracts-check`, `make skillpacks-validate` sau mỗi role mới;
  `make services-test-company` cho activation service.
- Phần B: `make agent-test` (coverage gate 80%) sau khi xoá `coordination/*` và wire
  `WorkflowEngine`/`SkillOptimizationLab`/`DurableApprovalService`; test luồng approval hợp
  nhất (tạo request → duyệt → resume) phải qua process thật, không chỉ instance thứ 2 cùng
  process (CLAUDE.md rule 6).
- `make verify` đầy đủ trước khi báo "xong" cho toàn bộ 2 phần.

## Open questions

1. Ưu tiên hoàn thiện functional profile nào trước trong nhóm 4 (cpo/chro/ciso/gc/cdo/caio) —
   theo nhu cầu thực tế của founder hiện tại hay theo độ khó tăng dần?
2. `WorkflowEngine`/`ParallelStep` nên áp dụng đầu tiên cho use case nào ngoài Executive Board
   (vd. chạy song song nhiều capability đọc-only cho 1 câu hỏi tổng hợp)?
3. Ai (role nào) chịu trách nhiệm approve `promote_skill_candidate` sau khi hợp nhất vào
   `DurableApprovalService` — vẫn `require_workspace_operator` hay mở rộng cho `founder` only,
   khớp với authority model của Executive Board (`role_id == 'founder'`)?

## Portfolio Closeout Evidence (2026-09-13)

Ghi nhận từ Task 5 (kế hoạch
`.superpowers/sdd/2026-09-12-caio-ai-governance-profile-and-executive-activation`)
— cổng closeout cuối cùng của toàn bộ 8 role Executive Board mới (`cro/sales`,
`vpe/coding`, `cpo/product`, `chro/people`, `ciso/security`, `gc/legal`,
`cdo/data`, `caio/ai_governance`). Mục tiêu: chứng minh không role nào tự kích
hoạt ngầm, và ghi trạng thái VERIFIED/UNVERIFIED trung thực dựa trên bằng chứng
chạy thật, không rubber-stamp.

### 1. Regression "không tự kích hoạt" (no-auto-activation)

Test mới `tests/e2e/test_executive_board_portfolio_closeout.py::test_new_project_has_all_new_profiles_as_templates_and_no_new_executive_roles_active`
tạo 1 Project thật hoàn toàn mới qua `POST /operations/projects`, đọc lại
`GET /operations/projects/:id/startup-team` và
`GET /operations/projects/:id/executive-roles` thật. Kết quả: **PASS**. Cả 8
functional profile mới đều `TEMPLATE`, cả 8 executive role mới đều
`UNAVAILABLE` (không phải `ACTIVE` hay bất kỳ trạng thái nào khác) trên 1
Project mới tinh — không có auto-activation ngầm nào. Các role tiền tồn tại
(`chief_of_staff`, `cfo`, `cmo`, `coo`, `cco`) vẫn hiện diện trong roster,
không bị phá vỡ.

### 2. Bảng VERIFIED/UNVERIFIED từng role (process E2E chạy thật, tại chỗ, 2026-09-13)

| Role key | Trạng thái | Lệnh chạy | Kết quả thật |
|---|---|---|---|
| `cro` (sales) | **VERIFIED** | `pytest tests/e2e/test_cro_sales_profile.py -v` | 1 passed |
| `vpe` (coding) | **VERIFIED** | `pytest tests/e2e/test_vpe_coding_profile.py -v` | 1 passed |
| `cpo` (product) | **VERIFIED** | `pytest tests/e2e/test_cpo_product_profile.py -v` | 2 passed |
| `chro` (people) | **VERIFIED** | `pytest tests/e2e/test_chro_people_profile.py -v` | 3 passed |
| `ciso` (security) | **VERIFIED** | `pytest tests/e2e/test_ciso_security_profile.py -v` | 3 passed |
| `gc` (legal) | **VERIFIED** | `pytest tests/e2e/test_gc_legal_profile.py -v` | 3 passed |
| `cdo` (data) | **VERIFIED** | `pytest tests/e2e/test_cdo_data_profile.py -v` | 3 passed |
| `caio` (ai_governance) | **VERIFIED** | `PGPASSWORD=<POSTGRES_PASSWORD thật trong .env> pytest tests/e2e/test_caio_ai_governance_profile.py -v` | 5 passed (cần disposable Postgres cluster thật; chạy lần đầu KHÔNG set `PGPASSWORD` khớp `.env` → 4 error "password authentication failed" — đây KHÔNG phải lỗi code, là thiếu bước môi trường đã biết, xem `docs/operations/executive-advisory-board-runbook.md` §8) |

**Tất cả 8/8 role VERIFIED** theo đúng định nghĩa của kế hoạch: "process E2E
có successful exit thật", không phải static check xanh.

### 3. `make verify` — kết quả từng target, phân loại rõ Xanh / Đỏ-đã-biết / Đỏ-MỚI

`make verify` chạy tuần tự và dừng ở target đỏ đầu tiên
(`lint`) — nên mỗi target còn lại được chạy TÁCH RIÊNG để có bằng chứng đầy
đủ, không suy diễn "toàn bộ đỏ" từ 1 lần dừng sớm.

| Target | Kết quả | Phân loại |
|---|---|---|
| `lint` | 72 lỗi ruff | **Đỏ, đã biết** — khớp baseline 77 lỗi ghi nhận tại Task 4 (`task-4-report.md`), xác nhận pre-existing trên `main`, không liên quan CAIO/8-role |
| `typecheck-py` | `error: Source file found twice under different module names: "agent.assets.contracts" và "packages.agent.assets.contracts"` (dừng luôn, 1 file) | **Đỏ, MỚI** — chưa từng ghi nhận trong lịch sử plan này. Nguyên nhân: `packages/agent/assets/{__init__,service,repository}.py` và một số nơi ở `apps/cosa/` import bằng tiền tố `from packages.agent.assets...` thay vì quy ước `from agent.assets...` toàn repo đang dùng (đến từ nhánh công việc "founder configurable assets", commit `be036229`/`c11a1560`, không thuộc phạm vi CAIO/8-role). Cần task riêng sửa import path, KHÔNG sửa trong Task 5 vì ngoài phạm vi role executive board |
| `boundary-check` | PASS | Xanh |
| `skillpacks-validate` | PASS | Xanh |
| `tenancy-check` | PASS (services/company vitest 247 file/1519 test; `tests/agent`+`test_tenant_isolation.py`; 3 file Flutter) | Xanh |
| `contract-freeze-check` | `company-usage-inventory.md lệch — chạy make company-usage-inventory và commit` | **Đỏ, MỚI** — snapshot generated cuối cùng khớp commit `7c377cce` (Task 4 của plan này); HEAD hiện tại `ef797caf` ("fix(workflows): enforce durable founder workflow authority", phiên khác, không thuộc plan CAIO) đã đổi company usage mà chưa regen snapshot. Không phải do Task 5 gây ra, cần phiên chủ của thay đổi đó tự regen+commit |
| `agent-test` | PASS — 1073 passed, 66 skipped, coverage 81.36% (gate 80%) | Xanh |
| `apps-cosa-test` | 15 failed, 1188 passed, 29 skipped | **Đỏ, đã biết** — 15 tên test FAIL khớp CHÍNH XÁC danh sách đã ghi tại Task 4 (`test_seed_publishes_every_deployed_agent_spec`, `test_project_crm_read_success`, 5 case `test_run_delegation.py`, 2 case `test_worker_wiring.py`, 2 case `test_founder_knowledge_context.py`, `test_lifecycle_tranche_c_acceptance.py`, `test_scheduled_session_worker.py`, `test_vertical_slice_1_read_path.py`, `test_workspace_execution_e2e.py`) — không có tên test mới nào xuất hiện |
| `services-test` (company + cosa) | PASS — company 247 file/1519 test; cosa 37 file/441 test | Xanh |
| `frontend-test` | PASS — 784 test, "All tests passed!" | Xanh |
| `frontend-analyze` | PASS — "No issues found!" | Xanh |
| `check-docs` | 2 broken relative doc link (`docs/architecture/plans/2026-08-29-cosa-workspace-canonical/M7-workforce-ui.md`, `M1-p0-security.md` → trỏ tới `packages/agent/coordination/{supervisor,approval_gate}.py`) | **Đỏ, pre-existing nhưng chưa từng ghi trong ledger plan này** — 2 file đã bị xoá tại commit `f8e960ff` ("refactor(agent): remove duplicate coordination primitives", 2026-09-12), là hệ quả của quyết định Phần B (§ "Quyết định thực thi B.1 + B.3" ở trên) đã chốt trong chính tài liệu này nhưng chưa dọn doc link cũ. Không liên quan CAIO/8-role, không sửa trong Task 5 |

`git diff --check` (whitespace) trên toàn bộ working tree: **sạch** (exit 0).

`make e2e-cross-plane-smoke`: **3 failed, 3 passed** — **Đỏ, MỚI, khác chữ ký
lỗi với bug đã biết trước đây.** `test_s2_dispatch_worker_result`,
`test_s3_capability_governance`, `test_s4_outbox_relay` đều fail vì bất nhất
`project_id`: `POST /agent/conversations` trên `apps/cosa` giờ đòi
`project_id` bắt buộc (`PROJECT_CONTEXT_REQUIRED`, xem
`apps/cosa/api/project_context.py`, từ commit `04afee16` "feat: require
project context for hub runs", 2026-09-11), trong khi `Envelope` outbox
(`apps/cosa/events/contracts.py`, `model_config = {"extra": "forbid"}`) lại từ
chối field `projectId` do Company gửi kèm ("Extra inputs are not permitted").
Đây KHÔNG phải bug "company-service-500" đã ghi nhận trước đây (task-9-report
của kế hoạch `2026-09-08-platform-authority-durability-hardening`) — chữ ký
lỗi hoàn toàn khác, xuất hiện SAU thời điểm plan đó đóng. Đây là phát hiện MỚI,
thật, ngoài phạm vi 8-role Executive Board, cần 1 task điều tra/sửa riêng
(khớp `project_id` bắt buộc ở route conversation với schema `Envelope` chưa
cập nhật theo).

### 4. Khung 5 trục (ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION) — 8 role

| Role | ACCEPTED | IMPLEMENTED | WIRED | VERIFIED | PRODUCTION |
|---|---|---|---|---|---|
| cro/sales | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — `COSA_EXECUTIVE_CRO_AGENT_SPEC` NẰM TRONG `COSA_DEPLOYED_AGENT_SPECS` (đã wired production deploy list) |
| vpe/coding | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — spec CHƯA nằm trong `COSA_DEPLOYED_AGENT_SPECS` (chỉ `EXECUTIVE_AGENT_SPECS`) |
| cpo/product | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — như trên |
| chro/people | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — như trên |
| ciso/security | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — như trên |
| gc/legal | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — như trên |
| cdo/data | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — như trên |
| caio/ai_governance | ✅ | ✅ | ✅ | ✅ (E2E pass) | Không xác nhận — như trên |

`ACCEPTED` chỉ xác nhận quyết định kiến trúc đã chốt trong tài liệu này;
`VERIFIED` ở đây nghĩa là process E2E thành công thật, không phải static
check xanh; `PRODUCTION` KHÔNG được suy diễn từ 4 trục kia — 7/8 role
(tất cả trừ `cro`) chưa được xác nhận nằm trong danh sách agent spec triển
khai production thật (`COSA_DEPLOYED_AGENT_SPECS`), đây là open item portfolio-
wide đã nêu 7 lần qua các Known Limitations của Task 4 mỗi role.

### 5. Open item portfolio-wide cần task riêng (không sửa trong Task 5)

1. **`COSA_DEPLOYED_AGENT_SPECS` thiếu 7 spec** (`vpe`, `cpo`, `chro`, `ciso`,
   `gc`, `cdo`, `caio`) — cần quyết định kiến trúc tường minh (thêm vào danh
   sách deploy production hay giữ nguyên là gap có chủ đích) trước khi coi các
   role này là `PRODUCTION`-ready.
2. **Read-capability HTTP-auth-unreachability** (portfolio-wide, cả 8 role):
   `*_read` capability gọi Company qua ambient COSA-delegation auth nhưng
   endpoint đọc dossier của Company bị khoá bởi `requireWorkspaceAccess` (chỉ
   chấp nhận `JWT_SECRET` human-session token) — không thể chạm tới từ 1 agent
   run thật hôm nay. Cần 1 thiết kế riêng cho auth surface giữa agent-run và
   Company read endpoint.
3. **`typecheck-py` mới đỏ** (mục 3 ở trên) — sửa import `packages.agent.assets.*`
   → `agent.assets.*` cho nhất quán, thuộc phạm vi "founder configurable
   assets", không thuộc phạm vi CAIO/8-role.
4. **`contract-freeze-check` mới đỏ** (mục 3 ở trên) — regenerate
   `docs/architecture/generated/company-usage-inventory.md` sau commit
   `ef797caf`, thuộc trách nhiệm phiên đã tạo thay đổi đó.
5. **`check-docs` đỏ do doc link chết** (mục 3 ở trên) — dọn 2 link trong
   `docs/architecture/plans/2026-08-29-cosa-workspace-canonical/{M7-workforce-ui,M1-p0-security}.md`
   trỏ tới file đã xoá theo quyết định Phần B của chính tài liệu này.
6. **`make e2e-cross-plane-smoke` mới đỏ 3/6 scenario** (mục 3 ở trên) — khớp
   `project_id` bắt buộc ở `POST /agent/conversations` với schema `Envelope`
   outbox chưa cập nhật để mang `projectId`; ngoài phạm vi 8-role, cần task
   điều tra riêng, có khả năng ảnh hưởng runtime thật (không chỉ test).
