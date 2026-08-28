# PART A — Adapt 18 pack (reference-only, không thực thi)

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §4, §5
**Nhánh đề xuất:** `msmk/part-a-adapt-skillpacks` (có thể tách 3 nhánh: `-a`, `-b`, `-c`)
**Phụ thuộc:** PART 0

## Context

18 pack ở §4 program cần chuyển từ nội dung upstream sang source material đã review, có
attribution, đúng contract Part 0. **Không** publish `SkillSpec`, **không** đăng ký capability,
**không** đụng `build_cosa_agent_plane()`. Đây là Phase A theo `docs/features/skills.md §17-18`
và hardening design D1: skillpack là reference material cho tới khi có Phase B capability-first.

Hiện trạng: 5 pack marketing (`positioning`, `market-research`, `copywriting`, `seo-plan`,
`campaign-review`) chỉ là công thức 4 dòng; 3 pack strategy (`evidence-synthesis`,
`experiment-design`, `decision-capture`) đã đầy hơn và đã khai tool call thật. 10 pack Nhóm B/C
chưa tồn tại.

## Nguyên tắc chung (mọi pack Nhóm A/B)

Mỗi `SKILL.md` sau adapt phải có, theo đúng cấu trúc pack strategy hiện có
(`skillpacks/strategy/evidence-synthesis/SKILL.md` làm mẫu tham chiếu):

1. Frontmatter `name` = `normalize_discovery_name(metadata.id)`, `description` trigger-oriented.
2. Mục tiêu + Khi nào dùng / KHÔNG dùng.
3. Điều kiện tiên quyết (input tối thiểu, schema).
4. Các bước tất định.
5. `## Tool Calls Được Phép (Allowed Tool Calls)` — khớp chính xác `manifest.runtime.tools`.
6. **Evidence requirement** — phân biệt evidence vs assumption; cấm bịa số liệu/testimonial.
7. **Safe fallback** khi capability chưa đăng ký: nêu "hành động không khả dụng", đưa kế hoạch
   non-mutating, không tuyên bố đã ghi.
8. Định dạng đầu ra.
9. Xử lý lỗi & edge case; **negative / prompt-injection case** nếu pack có web input.
10. `## Nguồn` — review record YAML (mẫu ở Part 0 §0.3).

`manifest.yaml` theo mẫu `skillpacks/marketing/positioning/manifest.yaml`: `apiVersion`, `kind`,
`metadata.{id,name,version,description}`, `publisher`, `source.path` = thư mục pack,
`capability.{domain,category,intents}`, `runtime.{entrypoint: SKILL.md, tools: [...]}`,
`permissions`, `risk`, `trust`.

Không copy nguyên kho / partner registry. Viết bằng thuật ngữ COSA + tiếng Việt nơi phù hợp.
Dependency liên-skill → tham chiếu `metadata.id` COSA, không tên tự do.

---

## PART A-A — Nhóm A (8 pack, giao trước)

Nâng cấp tại chỗ, giữ `metadata.id` cũ, **bump version** (`1.0.0 → 1.1.0`).

| Pack | File | Ghi chú riêng |
| --- | --- | --- |
| `marketing.positioning` | `skillpacks/marketing/positioning/{manifest.yaml,SKILL.md}` | `runtime.tools: []`. Thêm template context: ICP, persona, JTBD, pain, alternative, objection, switching force, customer language, proof point, brand voice. Nêu rõ evidence vs assumption cho từng mục. |
| `marketing.market-research` | `skillpacks/marketing/market-research/*` | `runtime.tools: [web.search]` (giữ) + safe fallback bắt buộc (capability chưa đăng ký tới Part SEARCH). Chèn 3 chế độ nghiên cứu (tài sản sẵn có / tín hiệu công khai / sơ cấp) + nguyên tắc `company-brain`: nguồn `unreviewed` không lấn át kết luận; quote nguyên văn; confidence/bias/recency; contradiction + gap + next steps. |
| `marketing.copywriting` | `skillpacks/marketing/copywriting/*` | `runtime.tools: []`. Brief dựa evidence; page/form audit checklist; headline/CTA variants; review-copy rubric; backlog experiment. Chỉ template, **không** publish trang. |
| `marketing.seo-plan` | `skillpacks/marketing/seo-plan/*` | `runtime.tools: [web.search]` + safe fallback. Intent cluster; content prioritization; AI-search visibility; technical audit checklist; structured-data checklist. **Không** deploy schema/website. |
| `marketing.campaign-review` | `skillpacks/marketing/campaign-review/*` | `runtime.tools: []`. Tracking plan; event/property taxonomy; UTM convention; source-of-truth; confidence/gap. |
| `strategy.evidence-synthesis` | `skillpacks/strategy/evidence-synthesis/*` | Giữ `runtime.tools: [strategy.evidence.list, strategy.evidence.create]` + `Allowed Tool Calls` hiện có. Thêm: facts vs inference, raw snapshot theo ngày, prompt-injection handling từ web (dossier đối thủ). |
| `strategy.experiment-design` | `skillpacks/strategy/experiment-design/*` | Thêm khung hypothesis / metric / sample-size / decision log. Giữ tool call hiện có nếu có. |
| `strategy.decision-capture` | `skillpacks/strategy/decision-capture/*` | Thêm: câu hỏi load-bearing, rationale, expected outcome, **revisit date**. `gateEvaluationId` là input context (theo hardening design §4.1.8), không phải call chưa khai. |

**File đụng thêm:** `docs/integrations/skill-source-attribution.md` (8 dòng `pending → adapted`),
`tests/agent_core/skills/test_skillpack_contract.py` (nếu cần chỉnh assert version).

---

## PART A-B — Nhóm B (7 pack mới)

Tạo domain mới. `source.path` phải trỏ đúng thư mục.

| Pack | Thư mục mới | `runtime.tools` | Nội dung |
| --- | --- | --- | --- |
| `strategy.competitor-profiling` | `skillpacks/strategy/competitor-profiling/` | `[web.search]` + safe fallback | Dossier template nhất quán; raw snapshot theo ngày; facts vs inference; prompt-injection từ website. Ghi rõ: tiêu thụ bởi recipe `sales/competitor-intelligence`. |
| `research.deep-research` | `skillpacks/research/deep-research/` | `[web.search]` + safe fallback | Research brief: citations, contradiction, gap, confidence, date/recency, next steps. Tiêu thụ bởi recipe `research/research-synthesize`. |
| `commercial.pricing` | `skillpacks/commercial/pricing/` | `[]` | Decision framework pricing/offer (từ `pricing` + `offers`). **Không** tự đặt giá — output là khuyến nghị + rủi ro. |
| `commercial.launch` | `skillpacks/commercial/launch/` | `[]` | Launch checklist + readiness gate. **Không** tự launch. |
| `commercial.revops` | `skillpacks/commercial/revops/` | `[]` | Battle card, lead lifecycle, RevOps cadence (từ `revops` + `sales-enablement`). |
| `commercial.churn-prevention` | `skillpacks/commercial/churn-prevention/` | `[]` | Retention analysis, at-risk signal framework. |
| `sales.prospecting` | `skillpacks/sales/prospecting/` | `[]` | Lead lifecycle framing. **Không** outbound (loại `cold-email`/`emails`/`sms`). |

**File đụng thêm:** `docs/integrations/skill-source-attribution.md` (7 dòng),
`tests/agent_core/skills/test_skillpack_contract.py` (đăng ký domain mới `commercial`, `research`,
`sales` vào tập hợp lệ + tăng số pack kỳ vọng).

---

## PART A-C — Nhóm C (3 meta pack, tầng policy·test·runbook)

Meta pack có skillpack tối thiểu (để validator + registry nhìn thấy) **cộng** artefact ở tầng
policy/test/runbook. **Không** pin vào `AgentSpec` nghiệp vụ.

| Pack | Thư mục skillpack | Artefact kèm |
| --- | --- | --- |
| `finance.cfo-review` | `skillpacks/finance/cfo-review/` | `docs/runbooks/cfo-review.md` (cash reconciliation, scenario, monthly/weekly cadence, anomaly checklist); phác capability contract Finance-Legal (connector grant bắt buộc) để Part C hiện thực. **Không** raw bank data vào prompt. |
| `platform.skill-adaptation` | `skillpacks/platform/skill-adaptation/` | `docs/development/skill-adaptation-policy.md` (keep/adapt/add, license gate, attribution bắt buộc, version bump, cross-skill impact review); rule mới trong `scripts/validate_skillpacks.py`: pack nào có `## Nguồn` với `upstream.repository` thì bắt buộc có `commit`, `license`, và một dòng tương ứng trong `skill-source-attribution.md`. CI check dòng ledger khớp. |
| `operations.loop-hardening` | `skillpacks/operations/loop-hardening/` | `docs/runbooks/loop-hardening.md` + test template tham chiếu `packages/agent_core/coordination/scheduler.py` (`coalescing_key`, `claim_token`, `max_attempts`), `runs/leases.py` (`RunLease` heartbeat), `capabilities/idempotency.py` (`IdempotencyClaimService`). Cấm cron local / self-wakeup trong prompt. |

**File đụng thêm:** `docs/runbooks/` (mới), `docs/development/skill-adaptation-policy.md` (mới),
`scripts/validate_skillpacks.py` (rule attribution), `tests/agent_core/skills/test_skillpack_contract.py`.

---

## Test

- `python scripts/validate_skillpacks.py` — 0 violation trên toàn bộ (16 + 18 = 34 pack); rule
  tool-chưa-đăng-ký chỉ bỏ qua `web.search` (whitelist); rule attribution bắt pack thiếu ledger.
- `python -m pytest tests/agent_core/skills/test_skillpack_contract.py -q` — xanh; assert 34 pack,
  đúng tập domain, đúng normalize name cho mọi `metadata.id` mới (vd `research.deep-research` →
  `research-deep-research`).
- **Không** test runtime nào đổi: `python -m pytest tests/apps/cosa/test_agent_plane_skillpack_boundary.py -q`
  vẫn xanh (đăng ký vẫn 5 capability).

## Verify

```text
python scripts/validate_skillpacks.py
python -m pytest tests/agent_core/skills/test_skillpack_contract.py tests/apps/cosa/test_agent_plane_skillpack_boundary.py -q
# kiểm tra ledger: mỗi pack A/B/C có đúng 1 dòng trong docs/integrations/skill-source-attribution.md, status=adapted
```

## Definition of Done

- [ ] 8 pack Nhóm A nâng cấp, bump version, đủ 10 mục cấu trúc, `Allowed Tool Calls` khớp manifest.
- [ ] 7 pack Nhóm B tạo mới ở domain đúng; B1/B2/`market-research`/`seo-plan` có safe fallback cho `web.search`.
- [ ] 3 meta pack Nhóm C có skillpack tối thiểu + runbook/policy/test template kèm.
- [ ] `skill-source-attribution.md`: 18 dòng `status=adapted`, mỗi dòng có `commit` + `license` + `upstream_version`.
- [ ] `validate_skillpacks.py` + `test_skillpack_contract.py` xanh với 34 pack.
- [ ] `test_agent_plane_skillpack_boundary.py` xanh — không capability nào bị thêm, không loader nào xuất hiện.
- [ ] Không có `publish_skill_spec()` nào được gọi trong phạm vi Part A.
