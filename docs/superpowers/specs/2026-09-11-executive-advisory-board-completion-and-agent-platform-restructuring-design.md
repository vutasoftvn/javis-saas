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
| coo, chief_of_staff | `"operations"` | `PENDING_OPERATIONS_PROFILE` — **không có key `"operations"` trong `STARTUP_TEAM_PROFILES`** (lệch tên/thiếu profile, cần điều tra) |
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
3. **Điều tra "operations"** (ưu tiên 3, làm sớm vì có thể chỉ là gap nhỏ): xác nhận
   `founder_assistant`/`cosa.agents.operations` có phải chính là profile `"operations"` mà
   `coo`/`chief_of_staff` cần hay không; nếu chỉ thiếu 1 mapping thì sửa nhanh, nếu là gap thật
   thì gộp vào nhóm 4.
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

**1. Hợp nhất lớp multi-agent orchestration.** Xoá
`packages/agent/coordination/{supervisor,delegate,quality_gate,risk_classification,synthesis,
scheduler,approval_gate}.py` (0 caller, trùng chức năng `WorkflowEngine`/`DurableApprovalService`/
`HttpControlPlaneSchedulerClient`), giữ `control_plane_scheduler_client.py` (đang live). Chọn
`WorkflowEngine` + `ParallelStep`/`AgentStep`/`ParallelBranch` làm con đường multi-agent DUY
NHẤT, wire vào `apps/cosa/composition/workflow_orchestration.py`.

**2. Nối vòng tự học/tự đề xuất cải tiến.** Wire `SkillOptimizationLab` vào `apps/cosa/worker/*`:
sau mỗi run dùng 1 skill, chạy `optimize()`, tự POST candidate qua `POST /candidates` với
`created_by_agent` được điền thật.

**3. Hợp nhất cơ chế phê duyệt.** Thay cơ chế duyệt tự chế của `POST /{id}/promote` bằng
`DurableApprovalService.create_approval_request(action="promote_skill_candidate", ...)`; mở
rộng `verify_and_prepare_resume` (hoặc thêm hàm chị em) để xử lý đề xuất không phải tool-call —
có 1 sổ phê duyệt/audit trail duy nhất cho mọi loại nâng cấp cần người duyệt.

**4. Feedback → tín hiệu học thật.** Dùng `aggregate_score` giảm dần làm tín hiệu tự động kích
hoạt `SkillOptimizationLab.optimize()`, thay vì là con số nằm im.

File cốt lõi: xoá `packages/agent/coordination/{supervisor,delegate,quality_gate,
risk_classification,synthesis,scheduler,approval_gate}.py` + test tương ứng; sửa
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
