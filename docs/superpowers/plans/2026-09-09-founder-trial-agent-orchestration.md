# Founder Trial — Node D: Domain-Agent Orchestration (POST-R1, Slice D)

> **Đây là node POST-R1.** Không nằm trong release Founder Trial R1.
> Blueprint: [`docs/superpowers/specs/2026-09-09-founder-trial-r1-reconciled-plan.md`](../specs/2026-09-09-founder-trial-r1-reconciled-plan.md).
> Spec sản phẩm §9 gọi đây là **Slice D**. R1 (node A0/A1/B/C/E) ship **không có
> agent chạy thật**; Founder Brief mặc định không có agent recommendation.

**Goal:** cho founder một Project Orchestrator điều phối Operations, CRM/Growth,
Marketing, Finance và Legal Guard qua durable work package, capability hẹp,
evidence input và human decision gate — **trên nền workforce bền vững đã có**,
không dựng cây agent tự cấp quyền.

---

## Preconditions (BLOCKING) — không bắt đầu D khi chưa đủ

Node D phụ thuộc plan **Persistent AI Workforce Governance**
([`plans/2026-09-09-persistent-ai-workforce-governance.md`](2026-09-09-persistent-ai-workforce-governance.md)).
Tính đến review 2026-09-09, workforce plan đã land Task 1–7A backend nhưng
**thiếu đúng những mảnh D cần**. D chỉ khởi động khi tất cả các mục sau đã
IMPLEMENTED + WIRED + VERIFIED (không phải chỉ ACCEPTED):

1. **Company-ward completion callback.** Worker (`apps/cosa/worker/work_package_run.py`)
   hiện chạy kernel nhưng **không có** callback báo hoàn thành kỹ thuật về
   Company → package kẹt ở `RUNNING`, không bao giờ tới `VALIDATION_PASSED` /
   `PENDING_MANAGER_REVIEW`. D Task 3 giả định path này tồn tại.
2. **Lease-claim delegation `operations.work_package.claim`.** Chưa được mint ở
   đâu (`work_package_run.py:15-17` ghi "nối tiếp ở slice sau").
3. **`skillpacks/operations/task-outcome-analysis/` được seed.** Hiện không tồn
   tại — làm hỏng cả Task 4A/7A/9 của chính workforce plan.
4. **Workforce Task 8** (Flutter workforce UI) và **Task 9** (disposable
   cross-plane E2E + `AI_WORKFORCE_V2_ENABLED` rollout guard + ops runbook) —
   chưa bắt đầu.

Nếu workforce chưa đạt bar này: **dừng**. Không "tạm build callback trong D"
(scope explosion), không chạy D trên workforce dở.

---

## Non-negotiable constraints

- Không nhân bản bảng employee/run/work package/attempt/queue/review từ
  workforce plan.
- Agent Platform không ghi Company business data trực tiếp — nhận signed
  delegation hẹp, gửi signed result tới Company-owned command.
- Mọi packet có `workspaceId, projectId, domain, objective, inputEvidenceRefs,
  outputSchemaKey, skillRef{key,version,checksum}, status, expiryAt, revision`.
- Không agent nào tự chọn domain, tự nâng capability, tự confirm plan, tự advance
  project, tự accept evidence, tự post accounting, tự gửi message, tự thực hiện
  payment, tự đổi nghĩa vụ pháp lý.
- **Legal Guard R1/Slice D = skill escalation/check, KHÔNG phải agent profile.**
  Không compliance verdict. Promote thành AgentSpec chỉ ở R2 nếu thật cần
  identity/capacity/scorecard (quy tắc 3).
- **CRM/Growth Slice D = skill `interview-synthesis` dispatch dưới Orchestrator.**
  AgentSpec/assignment riêng cho CRM/Growth chỉ khi cần identity/capacity/scorecard.
- Agent phải trả input gap + uncertainty. LLM answer không thành financial/
  customer evidence nếu chưa qua human review hiện có.

---

## Câu hỏi hoãn tới lúc bắt đầu D (ghi nhận, không quyết trước)

**Mô hình lưu domain packet.** Hai lựa chọn, quyết khi bắt đầu D dựa trên hình
dạng `ai_work_packages` lúc đó:

- **(a) Extend** `ai_work_packages` (Company migration 52) thêm cột
  `project_id, domain, objective, input_evidence_refs, output_schema_key` +
  một bảng nhỏ `domain_packet_drafts` **chỉ** cho giai đoạn `DRAFT` /
  `AWAITING_CONFIRMATION` trước confirm. Một máy trạng thái runtime duy nhất
  (`WorkPackageStatus` hiện có). Tuân quy tắc 4. **Ưu tiên.**
- **(b) Bảng riêng** `project_domain_work_packets` với enum 10 trạng thái —
  chỉ chọn nếu (a) chứng minh không khả thi; kèm ADR giải thích vì sao chấp
  nhận 2 máy trạng thái.

Không tạo migration 56 trước khi chốt.

---

## Task D1 — Project/domain envelope trên work-package contract hiện có

**Files:** (tùy lựa chọn a/b ở trên)
- `services/company/operations/services/project-domain-work-packet.service.ts`
- Modify `services/company/operations/services/work-package.service.ts`
- Migration Company mới (số kế tiếp lúc đó), expand-only, có down
- `services/company/operations/tests/project-domain-work-packet.service.test.ts`

**Test đỏ:** Company-side project ownership; domain allowlist
(`ORCHESTRATION|OPERATIONS|CRM_GROWTH|MARKETING|FINANCE|LEGAL_GUARD`); mọi
`inputEvidenceRefs` cùng workspace; packet `DRAFT` không vào workforce queue;
founder confirmation tạo đúng **một** work package (idempotent); expired packet
không dispatch được; audit event immutable; rework tạo revision, không ghi đè output.

**Triển khai:** validate policy + project/tenant + expected revision **trước khi**
gọi workforce package command. **Tái dùng** assignment/lease/cancellation/
manager-review flow của workforce. Chỉ lưu record ID + structured input snapshot
cần cho reproducibility — không credential, không prompt transcript.

## Task D2 — R1 roster + typed skills

**Files:**
- Modify `apps/cosa/agents/specs.py`, `apps/cosa/agents/agent_profile_specs.py`
- Modify `packages/agent/workforce/composition.py`
- Create `skillpacks/operations/founder-lifecycle-proposal/*`
- Create `skillpacks/crm_growth/interview-synthesis/*`
- Create `skillpacks/marketing/experiment-draft/*`
- Create `skillpacks/finance/cash-observation-summary/*`
- Create `skillpacks/legal/guard-escalation/*`  ← domain `legal` chưa tồn tại, tạo mới
- Tests `tests/apps/cosa/agents/test_founder_trial_agent_specs.py`,
  `tests/skillpacks/test_founder_trial_skill_contracts.py`

**Test đỏ:** roster có Project Orchestrator + Operations + Marketing + Finance,
mỗi cái có purpose + allowed capability set + input/output schema. **CRM/Growth
và Legal Guard xuất hiện như skill** (không phải agent profile) trừ khi review
lúc đó quyết định ngược lại. Finance skill không thể confirm document/reconcile/
payment; Legal Guard skill không claim legal applicability; skill version/checksum
lạ không dispatch được.

**Triển khai:** Project Orchestrator nhận capability lifecycle-read + proposal +
packet-draft. Skill định nghĩa structured output, evidence provenance requirement,
uncertainty fields, max action class, pinned version/checksum. `compose_workforce`
(stage-aware catalog) **chỉ là recommendation filter**, không phải dispatch authority.

## Task D3 — Dispatch signed project-domain packet + nhận typed result

**Files:**
- Modify `apps/cosa/events/*` (intake/validation), `apps/cosa/worker/work_package_run.py`
- Create `apps/cosa/worker/project_domain_packet_run.py` nếu cần adapter hẹp
- Modify `services/company/operations/services/project-domain-work-packet.service.ts`
- Create `services/company/operations/handlers/project-domain-work-packet.handler.ts`
- Tests cross-plane (disposable DB + real signed event fixture)

**Test đỏ:** emitted Company packet mang opaque workspace/project/packet ID +
signed provenance + pinned skill facts; replay dedupe; run cho workspace khác bị
từ chối; packet cancelled/expired không gọi tool được; result callback yêu cầu
expected packet revision và **không đổi được plan/cycle status**; structured
output lỗi → `READY_FOR_REVIEW` kèm error, không thành task chạy được.

**Triển khai:** delegation scope `{workspace, project, packet, work-attempt,
capability, expiry}`. Runner load exact employee assignment + skill pin từ
workforce, **không** chọn từ model text. Company verify callback signature +
retry/idempotency key + state transition rồi lưu structured result là **proposal
để review**. Field tài chính/pháp lý/external-action bị từ chối trừ khi có
command người riêng cho phép.

## Task D4 — Founder review: chỉ proposal được accept mới thành work

**Files:**
- Modify `venture-lifecycle-plan` hoặc `founder-trial-board` service tùy R1.1
- Modify `project-domain-work-packet` service + handler
- Modify `frontend/lib/modules/strategy/founder_trial/*`
- Create `frontend/test/modules/strategy/domain_packet_review_test.dart`

**Test đỏ:** orchestrator proposal có sources + confidence + input gaps; founder
edit/confirm/reject/defer; accept domain packet → tạo governed work package hiện
có; reject không đụng strategy evidence hay project stage; agent result **không**
làm payment/campaign send/legal filing/stage transition.

**Triển khai:** flow gọn: objective → evidence consumed → proposed output →
confidence/gaps → founder choice → resulting governed work item. Dùng
`WorkspaceCapabilityManifest` để hiện agent unavailable là unavailable, không
phải card AI trống. **Không** expose prompt console tự do làm control surface
chính của R1.

## Task D5 — Prove E2E + đặt gate roadmap kế

**Test đỏ → xanh:** kịch bản project thật: confirm lifecycle chỉnh tay bằng tay
→ attach reviewed CRM/marketing/finance input → tạo Operations packet → dispatch
1 pinned skill → review result → materialize 1 confirmed task. Kèm replay,
cancellation, stale revision, cross-tenant.

```
make company-boundary-check encore-handler-boundary-check frontend-api-contract-check mvp-surface-check lease-integration-test e2e-cross-plane-smoke
```
+ disposable Postgres/process test cho work-package lease, cancellation, callback
recovery. Static spec + mock-only test + README **không** đủ evidence.

**Gate roadmap (đặt, không implement ở đây):**
- **R1.1** có thể thêm `venture_lifecycle_plans` (versioned, multi-phase, AI
  proposal, diff/amend/revert, workflow xác nhận riêng) — chỉ khi founder trial
  chứng minh cần đồng thời tất cả các yếu tố đó. Và Vision/Mission/Value.
- **R1.2** thêm PESTEL/SWOT/TOWS/BSC chỉ khi mỗi artifact có decision consumer +
  version/review policy khai báo.
- **R2** legal pack sâu, thêm connector, CRM/finance workflow đầy đủ — chỉ sau
  khi regulation scope + human approval model được đặc tả riêng.
- Vault/RAG, voice, autonomous outbound/spend, free workflow builder giữ PLANNED
  tới khi có backend contract + safety gate được duyệt.
