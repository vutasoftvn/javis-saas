# Executive Board — Remaining Role Portfolio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute one role plan at a time. Do not parallelise plans that touch the same Startup Team catalog or Company migration sequence.

**Goal:** Hoàn thành có kiểm soát tám role còn lại của Executive Advisory Board — `cro`, `vpe`, `cpo`, `chro`, `ciso`, `gc`, `cdo`, `caio` — mà không biến advisory board thành đường tác động tự động hay làm giả readiness.

**Architecture:** Mỗi role có hai lớp tách biệt: functional profile là workforce identity chạy được, còn executive role là advisory-only composition, lấy đúng assignment/spec/skill pin tại lúc tạo deliberation frame. Company giữ Project roster, activation và board ledger; Agent Platform chỉ resolve exact-hash spec, thực hiện capability đã được cấp, và không ghi Company DB trực tiếp. Role chỉ từ `UNAVAILABLE` sang `AVAILABLE_NOT_ACTIVATED` sau khi profile nền, skillpack, registry và E2E đều có bằng chứng xanh.

**Tech Stack:** Shared JSON contracts + Node generators; Encore/TypeScript/Drizzle/PostgreSQL (Company); Python/Agent SDK (COSA); hash-pinned skillpacks; Flutter/GetX; Vitest, pytest, Flutter tests, disposable PostgreSQL/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`

## Global Constraints

- Đây là portfolio kế tiếp Phase 1, B.1/B.3, B.2/B.4 và Operations; một plan predecessor chỉ là thiết kế cho đến khi gate của nó xanh ở runtime.
- Founder/Admin kích hoạt functional profile bằng CAS/idempotency hiện hữu; chỉ Founder con người được activate/disable executive role. Không profile nào tự tạo board activation, preset activation hoặc external side effect.
- Mọi advisor giữ `advisoryOnly: true`, `L1_PROPOSE` hoặc thấp hơn, capability-empty trong AgentSpec executive và không được dùng để gửi mail, deploy, thanh toán, tuyển dụng, ký kết, thay đổi policy hay truy cập secret.
- `shared/contracts/startup-team-profiles.json` và `shared/contracts/executive-advisor-roles.json` là nguồn catalog. Không hand-edit generated TS/Python/Dart; chạy generator và `make contracts-check`.
- Mỗi profile mới phải có explicit mapping ở Company `OwnerAgentProfile`, `AGENT_PROFILE_SPEC_ID/VERSION/HASH`, Agent Platform `AGENT_PROFILE_SPECS`, `COSA_DEPLOYED_AGENT_SPECS`/seed và exact `AgentSpec` hash. Không fallback theo string hoặc alias `founder_assistant`.
- Mọi Company record và agent run dùng `workspace_id` + `project_id` bất biến, membership server-side, opaque string ID ở JSON/Flutter. Cross-project/workspace evidence phải fail closed.
- Migration chỉ additive. Backfill chỉ tạo `TEMPLATE` profile/assignment; không tạo `ACTIVE` assignment hoặc executive activation. Down migration từ chối nếu profile/assignment đã được activate hay được frame tham chiếu.
- Không ghi dữ liệu nhạy cảm/raw PII/secret/prompt vào knowledge, log, skillpack hay board frame. Dùng metadata đã phân loại, redaction và source reference Project-bound.

## Dependency and release order

| Order | Plan | Hard entry evidence | New functional profile | Role becomes eligible when |
| --- | --- | --- | --- | --- |
| 1 | `2026-09-12-cro-sales-profile-and-executive-activation.md` | CRM/Sales plan has real service + Project E2E | `sales` | pipeline/evidence reads are project-bound and Sales is `ACTIVE` |
| 2 | `2026-09-12-vpe-coding-profile-and-executive-activation.md` | safe-local-executor grants, sandbox and receipt E2E pass | `coding` | only read-only engineering evidence is available; no raw shell path |
| 3 | `2026-09-12-cpo-product-profile-and-executive-activation.md` | Project decision-dossier contract/E2E passes | `product` | product evidence is immutable, Project-bound and redacted |
| 4 | `2026-09-12-chro-people-profile-and-executive-activation.md` | people-risk dossier/E2E passes | `people` | no personnel PII is exposed to model or board |
| 5 | `2026-09-12-ciso-security-profile-and-executive-activation.md` | security posture intake/E2E passes | `security` | posture evidence contains no secrets and access stays read-only |
| 6 | `2026-09-12-gc-legal-profile-and-executive-activation.md` | legal issue dossier/E2E passes | `legal` | Company legal applicability remains source-of-truth, no legal conclusion action |
| 7 | `2026-09-12-cdo-data-profile-and-executive-activation.md` | data inventory/quality E2E passes | `data` | only classified metadata/provenance is reachable |
| 8 | `2026-09-12-caio-ai-governance-profile-and-executive-activation.md` | model-policy/evaluation snapshot E2E passes | `ai_governance` | Control Plane remains read-only from the advisor path |

The eight plans deliberately serialize catalog migrations as `008` through `015`, after Operations `007`. Before executing any migration task, compare the live migration directory and applied schema table; if another approved migration has claimed a number, renumber only the unexecuted plan and its tests before writing SQL. Never rename an applied migration.

## Shared acceptance model

```text
catalog TEMPLATE + exact AgentSpec/skill pin + profile-specific evidence gate
      -> founder activates functional profile (CAS, v2)
      -> Board reports AVAILABLE_NOT_ACTIVATED
      -> founder explicitly activates role (CAS, v2)
      -> deliberation frame snapshots assignment/spec/skill hashes

missing / stale / cross-project evidence / inactive assignment
      -> UNAVAILABLE or rejected request; never model fallback
```

### Task 1: Execute the portfolio without readiness inflation

**Files:** Use the eight linked role plans; modify only the plan currently being executed.

**Interfaces:** Each role plan produces one catalog profile, one AgentSpec mapping, one capability-empty executive spec, one `skillpack:executive/<role>-advisor@1.0.0`, and a Project-scoped E2E proof. The next plan consumes only committed predecessors.

- [ ] **Step 1: Establish the entry gate**

```bash
git status --short
make executive-board-verify
make contracts-check
```

Expected: existing dirty files remain untouched; Phase 1/Operations evidence is green or the executor stops and records the failed predecessor rather than changing role readiness.

- [ ] **Step 2: Select exactly one role plan in dependency order**

Read the plan, verify all named predecessor gates, and create a branch-free implementation checklist. Do not edit a later catalog entry merely to make a board card look available.

- [ ] **Step 3: Run role-local red/green gates and cross-plane proof**

```bash
make contracts-check
make skillpacks-validate
make services-test-company
make agent-test
make frontend-api-contract-check
```

Expected: targeted tests specified in the selected plan pass before broad gates; any environment-blocked process E2E is reported as unverified, not passed.

- [ ] **Step 4: Commit exactly one role release**

```bash
git add shared/contracts services/company/operations apps/cosa skillpacks/executive frontend tests
git commit -m "feat(executive-board): activate <role> advisor"
```

Expected: replace `<role>` with the actual single role; do not stage unrelated user work.

## Portfolio exit evidence

- Eight `READY` catalog roles have an active functional assignment and explicit Founder activation path; no inactive profile can be selected into a deliberation.
- One disposable PostgreSQL/process scenario per role proves foreign workspace/project denial, inactive-profile denial, exact skill/spec pin snapshot, no direct Agent-DB Company write, and no auto-activation.
- Flutter obtains status and mutation receipts from Company then reloads authoritative role state; it never reconstructs readiness from title/domain strings or optimistic mutation payloads.
- `make verify` is green only after every individual E2E is green; otherwise the release note names the exact unverified boundary.
