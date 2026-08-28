# Chương trình tích hợp `marketingskills` + `makerskills` vào COSA

**Ngày:** 2026-08-28
**Trạng thái:** Đã duyệt để thực hiện dần (chủ sở hữu chốt 2026-08-28)
**Quan hệ tài liệu:** mở rộng và thay thế phần lộ trình của
[`2026-08-28-marketingskills-makerskills-adoption-plan.md`](./2026-08-28-marketingskills-makerskills-adoption-plan.md)
(giữ doc đó làm phân tích nguồn). Kế hoạch chi tiết từng phần nằm ở `docs/implementation/2026-08-28-msmk-part*.md`.

---

## 1. Context — vì sao làm việc này

`2026-08-28-marketingskills-makerskills-adoption-plan.md` là bản khuyến nghị mức chiến lược:
adapt có chọn lọc hai kho MIT (`coreyhaines31/marketingskills` 50 skill,
`coreyhaines31/makerskills` 20 skill) để làm sâu các skill marketing/strategy của COSA, theo
capability-first + workspace-first + immutable SkillSpec. Doc đó chưa phải plan thực thi: không
schema cụ thể, không danh sách file, không thứ tự phụ thuộc, một số tiền đề chưa đối chiếu code.

Đã đối chiếu toàn bộ tiền đề với code thật. Mọi tuyên bố cấu trúc trong doc **đúng**; lộ thêm vài
điểm doc đánh giá nhẹ (§3). Chương trình này biến khuyến nghị thành các Part độc lập, thứ tự phụ
thuộc rõ, test + Definition of Done cho từng Part.

**Quyết định phạm vi đã chốt (2026-08-28):**

| # | Quyết định |
| --- | --- |
| 1 | Một chương trình bao trùm Phase 0→C, cấu trúc thành Part độc lập giao dần. |
| 2 | Gộp việc dựng API marketing-context canonical vào chương trình (Part CTX). |
| 3 | Adapt **đủ 18 pack** theo danh mục bất biến §4. |
| 4 | Schema marketing-context dùng **schema lai**: chuẩn hoá phần cần join theo confidence/evidence, giữ jsonb phần ít truy vấn. |
| 5 | `web.search` = **Tavily production adapter thật**, thiết kế đổi provider được, kèm quota/budget/audit per workspace. |
| 6 | Skill Registry HTTP backend nằm trong scope (Part REG). |
| 7 | Evals, tenancy isolation, approval bind/resume, restart recovery, provider sandbox là **gate bắt buộc trước production**. |

---

## 2. Đối chiếu doc gốc ↔ code thật (đã verify)

| Tuyên bố | Kết quả | Bằng chứng |
| --- | --- | --- |
| 16 source skillpack, 5 pack marketing mỏng | Đúng. `skillpacks/marketing/positioning/SKILL.md` chỉ 4 dòng. `skillpacks/strategy/*` đã đầy hơn và đã khai tool call (`strategy.evidence.create`, `risk_level: medium`). | `skillpacks/` — 1 core + 5 marketing + 7 strategy + okr + tasks + twelve-week-year |
| `SkillSpec`/`SkillResolver`/`publish_skill_spec()`/`PinnedSkillRef`; resolve theo `id+version+definition_hash`, hash lệch fail trước khi tạo run | Đúng nguyên văn. `SkillSpec` có `instructions`, `required_capabilities`, `required_knowledge`, `references`. Hash trên `id+version+instructions+sorted(required_capabilities)`. | `packages/agent_core/skills/contracts.py:65`, `resolver.py:33`, `registry/publisher.py`, `contracts/identity.py:41` |
| `skillpacks/` source-only; plane chỉ đăng ký capability tường minh; regression test cấm scan skillpack | Đúng. `build_cosa_agent_plane()` đăng ký đúng 5 capability. Test grep chuỗi `"skillpacks"` trong module plane + mọi handler module. | `apps/cosa/composition/agent_plane.py:279-283`, `tests/apps/cosa/test_agent_plane_skillpack_boundary.py` |
| `web.search` được recipe khai nhưng chưa đăng ký | Đúng. `market-research` + `seo-plan` manifest khai `tools: [web.search]`; recipe `research/research-synthesize` + `sales/competitor-intelligence` khai `requires.capabilities: [web.search]`. Zero đăng ký. | `packages/agent_recipes/*/recipe.yaml`, `docs/development/add-capability.md` |
| Mâu thuẫn contract skillpack giữa tài liệu | Đúng. `docs/development/add-skill.md:17` nói `skill.yaml` tại `packages/agent_core/skills/library/<id>/`. Validator + hardening design + skills.md + cả 16 pack thực tế dùng `manifest.yaml`+`SKILL.md` tại `skillpacks/<domain>/<id>/`. | `packages/agent_core/skills/skillpack_contract.py`, `docs/features/skills.md:30` |
| `commercial.marketing_contexts` cần trường cấu trúc/provenance | Đúng, nặng hơn: bảng jsonb trần (`category, market, positioning, pricing, channels`), không revision/provenance/review_status/evidence. Không service, không handler, không API nào chạm. | `services/company/shared/db/schema/commercial.ts:117-128` |
| Marketing Cockpit gọi route lệch backend | Đúng, nặng hơn: `frontend/lib/modules/marketing/services/marketing_service.dart` gọi 10+ route `/marketing/context/*` — 404 ở mọi backend. | `marketing_service.dart:118-383` |
| Knowledge ingestion / approval / scheduler / idempotency là khối compose được | Đúng. Ingestion sau flag `knowledge_ingestion_enabled()`; pipeline QUEUED→VALIDATING→preflight→scan→convert→normalize→persist candidate→record control plane; `authority_class` ∈ REFERENCE/POLICY/BUSINESS_SNAPSHOT/USER_CONTENT/EXTERNAL; `ingest_status` review_pending→published/rejected. Retrieval chưa wire. | `apps/cosa/knowledge_ingestion/handler.py`, `packages/agent_core/knowledge/models.py:38-50`, `apps/cosa/api/routes.py:1088` |
| Approval bind `run_id + tool_call_id + checkpoint_ref` | Đúng nguyên văn. `create_approval_request(run_id, tool_call_id, checkpoint_ref)`; `verify_and_prepare_resume()` kiểm target drift + ambient governance + re-evaluate policy. | `packages/agent_core/capabilities/approval_service.py:92,229` |
| Finance-Legal có snapshot/transaction workspace-scoped + approval | Đúng. `financial_transactions.approvalStatus`, `POST /finance-legal/transactions/:id/approve`. | `services/company/shared/db/schema/finance-legal.ts:31-79` |

---

## 3. Điểm doc gốc đánh giá nhẹ

1. **Phase B bị chặn độc lập với chương trình này.** Part 1 của
   [`2026-08-28-dev-readiness-remediation-remaining`](../implementation/2026-08-28-dev-readiness-remediation-remaining.md)
   (tenant scope query-layer cho 7 service commercial + finance-legal) **chưa xong**; cùng doc
   liệt kê "Không broad-activate skillpack runtime" là non-goal. → Part B/C và Part CTX phụ thuộc
   cứng Part 1 remediation.
2. **Flutter Skill Registry UI** (`frontend/lib/modules/skills/`) gọi `/skills/*` — **không có
   backend** ở cả COSA FastAPI (`/agent/*` only) lẫn Encore. → Part REG dựng HTTP backend.
3. **Recipe tham chiếu skill bằng floating path** `ref: skillpacks/strategy/evidence-synthesis`
   — đúng anti-pattern `SkillResolver` chặn. Chuyển sang `PinnedSkillRef` ở Part B3.
4. Thuật ngữ: `strategy.evidence-synthesis` là **skillpack**, không phải recipe. Recipe thật là
   `research/research-synthesize`.

---

## 4. Danh mục 18 pack (bất biến — chốt 2026-08-28)

### Nhóm A — Nâng cấp skillpack runtime đã có (8)

| # | Pack id | Nguồn upstream | Trọng tâm adapt |
| --- | --- | --- | --- |
| A1 | `marketing.positioning` | marketingskills/product-marketing | ICP, persona, JTBD, pain, alternative, objection, switching force, customer language, proof point, brand voice; evidence vs assumption; version/changelog. |
| A2 | `marketing.market-research` | customer-research + deep-research (chế độ) + company-brain (nguyên tắc) | 3 chế độ (tài sản sẵn có / tín hiệu công khai / sơ cấp); quote nguyên văn; confidence/bias/recency; contradiction + gap + next steps; nguồn chưa review không lấn át. |
| A3 | `marketing.copywriting` | copywriting, copy-editing, cro, signup, onboarding, paywalls, popups | brief dựa evidence, page/form audit, headline/CTA variants, review copy, backlog experiment. |
| A4 | `marketing.seo-plan` | seo-audit, ai-seo, schema, site-architecture, content-strategy | intent cluster, content prioritization, AI-search visibility, technical audit, structured-data checklist. |
| A5 | `marketing.campaign-review` | analytics, attribution, ab-testing | tracking plan, event/property taxonomy, UTM, source-of-truth, confidence/gap. |
| A6 | `strategy.evidence-synthesis` | competitors | facts vs inference; raw snapshot theo ngày; prompt-injection handling. Giữ tool call `strategy.evidence.*` hiện có. |
| A7 | `strategy.experiment-design` | ab-testing | hypothesis / metric / sample-size / decision log. |
| A8 | `strategy.decision-capture` | decide | câu hỏi load-bearing, rationale, expected outcome, revisit date. Giữ `gateEvaluationId` là input context. |

### Nhóm B — Skillpack runtime mới, provider-dependent / commercial (7)

| # | Pack id | Nguồn | Trọng tâm | Provider |
| --- | --- | --- | --- | --- |
| B1 | `strategy.competitor-profiling` | competitor-profiling | dossier theo template; tiêu thụ bởi recipe `sales/competitor-intelligence` | `web.search` |
| B2 | `research.deep-research` | deep-research | research brief có citation, contradiction, gap, confidence, date; tiêu thụ bởi recipe `research/research-synthesize` | `web.search` |
| B3 | `commercial.pricing` | pricing, offers | decision framework pricing/offer; không tự đặt giá | — |
| B4 | `commercial.launch` | launch | launch checklist; không tự launch | — |
| B5 | `commercial.revops` | revops, sales-enablement | battle card, lead lifecycle, RevOps cadence | — |
| B6 | `commercial.churn-prevention` | churn-prevention | retention analysis, at-risk signal | — |
| B7 | `sales.prospecting` | prospecting | lead lifecycle framing; không outbound | — |

### Nhóm C — Meta pack ở tầng policy·test·runbook, không pin vào agent nghiệp vụ (3)

| # | Pack id | Nguồn | Hình thức triển khai |
| --- | --- | --- | --- |
| C1 | `finance.cfo-review` | company-cfo | Runbook + eval + capability contract Finance-Legal; connector grant bắt buộc; không raw bank data vào prompt. |
| C2 | `platform.skill-adaptation` | skillify + pm/toolify checklist | Policy doc + validator rule + CI check: keep/adapt/add, license gate, attribution, version bump, cross-skill impact review. Thay commit tự động bằng candidate→eval→human approval→immutable publish. |
| C3 | `operations.loop-hardening` | loopify | Runbook + test template: idempotency key, transaction, retry/rate limit, first-run verification, bail-out. Trỏ `packages/agent_core/coordination/scheduler.py` + `runs/leases.py`; cấm cron local / self-wakeup trong prompt. |

**Loại vĩnh viễn:** `ads`, `ad-creative`, `cold-email`, `emails`, `sms`, `social`,
`directory-submissions`, `influencer-marketing`, `events`, `image`, `video` (marketingskills);
`second-brain`, `personal-cfo`, `domain`, `paste`, `jab-hook`, `slide-deck`, `watch-video`,
`social-fetch` (makerskills). `company-brain` → chèn nguyên tắc vào A2/B2 + taxonomy §5.
`pm`/`toolify` → gộp checklist vào C2.

---

## 5. Cấu trúc chương trình và thứ tự phụ thuộc

```
Part 0    Reconcile + governance readiness (inventory 18 hạng mục)         ── không phụ thuộc
Part A-A  Adapt Nhóm A (8 pack, reference-only)                            ── sau Part 0
Part A-B  Adapt Nhóm B (7 pack, reference-only)                            ── sau Part A-A
Part A-C  Adapt Nhóm C (3 meta pack: policy/test/runbook)                  ── sau Part A-A
Part CTX  Marketing Context canonical API (schema lai) + Cockpit rewire    ── sau Part 0; PHỤ THUỘC Part 1 remediation
Part SEARCH  web.search capability — Tavily production adapter             ── sau Part 0
Part REG  Skill Registry HTTP backend (AgentOS) + Flutter routing          ── sau Part 0
Part B1   Runtime slice: context & copy drafting (artifact-only)           ── sau A-A + CTX + REG + tenancy gate
Part B2   Runtime slice: research brief (read-only external)               ── sau B1 + SEARCH
Part B3   Runtime slice: curated knowledge & competitive intelligence      ── sau B2
Part C    Business writes + external integrations (mỗi provider 1 sub-plan) ── sau B*
```

**Gate toàn cục Part B/C + Part CTX:** `make tenancy-check` xanh + Part 1 remediation
(`2026-08-28-remediation-part1-tenant-query-scope.md`) merge. Trước đó làm được Part 0 / A-* /
SEARCH / REG / phần Encore của CTX (không ship).

**Gate bắt buộc trước production (mọi Part B/C):**
- eval suite xanh (4 path: happy / missing-evidence / stale-contradictory / prompt-injection);
- tenancy isolation test (cross-workspace deny);
- approval bind + resume test;
- restart recovery E2E qua durable worker thật — không instance thứ hai cùng process (CLAUDE.md #6);
- provider sandbox/fixture test.

---

## 6. Taxonomy evidence/provenance (dùng chung mọi Part)

Trường: `source_url`, `captured_at`, `captured_by`, `workspace_id`, `confidence`
(`low|medium|high`), `trust` (`unreviewed|verified|deprecated|superseded`), `sensitivity`
(`public|internal|confidential`), `review_status`, `supersedes`, `evidence_id`.

Ánh xạ sang cái đã có: `KnowledgeDocument.authority_class`
(REFERENCE/POLICY/BUSINESS_SNAPSHOT/USER_CONTENT/EXTERNAL) + `ingest_status`. Taxonomy mới **bổ
sung**, không thay `authority_class`. Chốt tại Part 0, ghi `docs/features/marketing-evidence-taxonomy.md`.

---

## 7. Kế hoạch chi tiết từng phần

| Part | Plan chi tiết | Nhánh đề xuất | Phụ thuộc |
| --- | --- | --- | --- |
| Part 0 | [msmk-part0-reconcile-governance](../implementation/2026-08-28-msmk-part0-reconcile-governance.md) | `msmk/part0-reconcile-governance` | — |
| Part A (A-A/A-B/A-C) | [msmk-part-a-adapt-skillpacks](../implementation/2026-08-28-msmk-part-a-adapt-skillpacks.md) | `msmk/part-a-adapt-skillpacks` | Part 0 |
| Part CTX | [msmk-part-ctx-marketing-context-api](../implementation/2026-08-28-msmk-part-ctx-marketing-context-api.md) | `msmk/part-ctx-marketing-context-api` | Part 0 + remediation Part 1 |
| Part SEARCH | [msmk-part-search-web-search-capability](../implementation/2026-08-28-msmk-part-search-web-search-capability.md) | `msmk/part-search-web-search` | Part 0 |
| Part REG | [msmk-part-reg-skill-registry-backend](../implementation/2026-08-28-msmk-part-reg-skill-registry-backend.md) | `msmk/part-reg-skill-registry` | Part 0 |
| Part B (B1/B2/B3) | [msmk-part-b-runtime-slices](../implementation/2026-08-28-msmk-part-b-runtime-slices.md) | `msmk/part-b1-context-copy` … | A-A + CTX + REG + gate |
| Part C | [msmk-part-c-business-writes](../implementation/2026-08-28-msmk-part-c-business-writes.md) | mỗi provider 1 nhánh | B* |

---

## 8. Rủi ro và điểm còn mở

1. **B*/C bị chặn bởi remediation Part 1** (ngoài kiểm soát chương trình này). Chỉ Part 0 / A-* /
   SEARCH / REG / Encore-CTX commit được ngày cụ thể; B*/C là "định hướng đã chốt, lịch mở".
2. **10 pack mới ở domain chưa tồn tại** (`skillpacks/commercial|sales|research|finance|platform`)
   — tăng bề mặt validator; không rủi ro runtime (reference-only).
3. **CTX schema lai**: ranh giới chuẩn-hoá/jsonb (`offer_architecture`, `twelve_week_plan` giữ
   jsonb) có thể phải đảo nếu sau này cần query sâu 2 mảng đó.
4. **Tavily**: khoá một nhà cung cấp + key ngoại + chi phí theo query. Adapter + `budget_store`
   per-workspace giảm rủi ro; vẫn cần chốt trần chi phí mặc định trước khi bật production.
5. **Part REG `sync-built-in`** phải publish có kiểm, tuyệt đối không thành auto-discovery runtime
   — dễ vô tình phá regression skillpack-boundary.
6. **18 pack là nhiều tuần Part A.** Nếu cần chứng minh giá trị sớm: A-A (8 pack) đủ cho B1/B2;
   A-B/A-C giao sau, không chặn B1.
