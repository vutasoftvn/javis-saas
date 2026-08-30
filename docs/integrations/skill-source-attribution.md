# Skill Source Attribution Ledger

**Ngày lập:** 2026-08-28  
**Chương trình:** [Chương trình tích hợp marketingskills + makerskills vào COSA](./2026-08-28-marketingskills-makerskills-program.md) · §4  
**Trạng thái:** Active (18/18 hạng mục gốc adapted; 1 đã `retired` — `marketing.positioning` — và kế thừa bởi 1 hàng bổ sung `strategy.positioning`, `pinned`, thêm 2026-08-31 khi hợp nhất nội dung tránh trùng lặp registry)

Tài liệu này là sổ cái (ledger) theo dõi nguồn gốc, commit snapshot, giấy phép và trạng thái thích ứng (adaptation) của tất cả các skillpack được adapt từ các kho mã nguồn bên ngoài vào COSA.

---

## 1. Bảng Inventory 18 hạng mục gốc + 1 hàng kế thừa (`strategy.positioning`, 2026-08-31)

| cosa_skill_id | nhóm | upstream_repo | commit_sha | upstream_skill(s) | upstream_version | license | status | last_reviewed | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `marketing.positioning` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `product-marketing` | `1.0.0` | MIT | `retired` | `2026-08-31` | ICP, persona, JTBD, pain, alternative, objection, switching force, customer language, proof point, brand voice; evidence vs assumption; version/changelog. **Retired 2026-08-31**: nội dung nghiệp vụ đã hợp nhất vào `strategy.positioning` (canonical ID, v1.1.0) để tránh trùng lặp registry; xem hàng `strategy.positioning` bên dưới. |
| `strategy.positioning` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `product-marketing` | `1.0.0` | MIT | `pinned` | `2026-08-31` | Kế thừa nội dung từ `marketing.positioning` (đã retire, xem hàng trên) khi hợp nhất vào ID canonical Tranche A. Cùng khung ICP/Persona/JTBD/Switching-forces/Evidence-vs-Assumption; đã chuẩn hoá theo template Triggers/Anti-triggers governance. Pinned vào `cosa.agents.marketing` (`apps/cosa/agents/specs.py`). |
| `marketing.market-research` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `customer-research`, `deep-research`, `company-brain` | `1.0.0` | MIT | `adapted` | `2026-08-28` | 3 chế độ (tài sản sẵn có / tín hiệu công khai / sơ cấp); quote nguyên văn; confidence/bias/recency; contradiction + gap + next steps; nguồn chưa review không lấn át. |
| `marketing.copywriting` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `copywriting`, `copy-editing`, `cro`, `signup`, `onboarding`, `paywalls`, `popups` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Brief dựa evidence, page/form audit, headline/CTA variants, review copy, backlog experiment. |
| `marketing.seo-plan` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `seo-audit`, `ai-seo`, `schema`, `site-architecture`, `content-strategy` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Intent cluster, content prioritization, AI-search visibility, technical audit, structured-data checklist. |
| `marketing.campaign-review` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `analytics`, `attribution`, `ab-testing` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Tracking plan, event/property taxonomy, UTM, source-of-truth, confidence/gap. |
| `strategy.evidence-synthesis` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `competitors` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Facts vs inference; raw snapshot theo ngày; prompt-injection handling. Giữ tool call `strategy.evidence.*` hiện có. |
| `strategy.experiment-design` | A | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `ab-testing` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Hypothesis / metric / sample-size / decision log. |
| `strategy.decision-capture` | A | `coreyhaines31/makerskills` | `33cb3870685a34522d91287869aef62170bdbcf7` | `decide` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Câu hỏi load-bearing, rationale, expected outcome, revisit date. Giữ `gateEvaluationId` là input context. |
| `strategy.competitor-profiling` | B | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `competitor-profiling` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Dossier theo template; tiêu thụ bởi recipe `sales/competitor-intelligence`; provider `web.search`. |
| `research.deep-research` | B | `coreyhaines31/makerskills` | `33cb3870685a34522d91287869aef62170bdbcf7` | `deep-research` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Research brief có citation, contradiction, gap, confidence, date; tiêu thụ bởi recipe `research/research-synthesize`; provider `web.search`. |
| `commercial.pricing` | B | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `pricing`, `offers` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Decision framework pricing/offer; không tự đặt giá. |
| `commercial.launch` | B | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `launch` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Launch checklist; không tự launch. |
| `commercial.revops` | B | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `revops`, `sales-enablement` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Battle card, lead lifecycle, RevOps cadence. |
| `commercial.churn-prevention` | B | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `churn-prevention` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Retention analysis, at-risk signal. |
| `sales.prospecting` | B | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `prospecting` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Lead lifecycle framing; không outbound. |
| `finance.cfo-review` | C | `coreyhaines31/makerskills` | `33cb3870685a34522d91287869aef62170bdbcf7` | `company-cfo` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Runbook + eval + capability contract Finance-Legal; connector grant bắt buộc; không raw bank data vào prompt. |
| `platform.skill-adaptation` | C | `coreyhaines31/makerskills` | `33cb3870685a34522d91287869aef62170bdbcf7` | `skillify`, `pm`, `toolify` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Policy doc + validator rule + CI check: keep/adapt/add, license gate, attribution, version bump, cross-skill impact review. |
| `operations.loop-hardening` | C | `coreyhaines31/makerskills` | `33cb3870685a34522d91287869aef62170bdbcf7` | `loopify` | `1.0.0` | MIT | `adapted` | `2026-08-28` | Runbook + test template: idempotency key, transaction, retry/rate limit, first-run verification, bail-out. Trỏ `packages/agent/coordination/scheduler.py` + `runs/leases.py`; cấm cron local / self-wakeup trong prompt. |

*Trạng thái hợp lệ cho `status`: `pending` → `adapted` → `published` → `pinned` (terminal) hoặc `retired` (terminal, khi nội dung đã hợp nhất vào một skill canonical khác và skillpack gốc đã bị xoá khỏi registry).*

---

## 2. Quy tắc quản trị nguồn (Source Governance Rules)

1. **Không dùng Git Submodule:** Mã nguồn bên ngoài được adapt thủ công thành source material bên trong repo COSA tại `skillpacks/<domain>/<id>/`. Tuyệt đối không thêm submodule hay pull repository bên ngoài lúc runtime.
2. **Không background auto-update:** Không cài đặt cron hay bot tự động kéo code từ upstream repo. Mọi thay đổi từ upstream phải được review thủ công, đánh giá tác động và nâng version có kiểm soát.
3. **Bản quyền và Attribution (MIT Notice):** Cả hai repository nguồn đều có giấy phép MIT. Khi sao chép hoặc thích ứng một phần đáng kể nội dung từ skill gốc, bắt buộc phải:
   - Ghi rõ nguồn `upstream.repository`, `commit` SHA 40 ký tự bất biến, `upstream_version` và `license: MIT`.
   - Giữ nguyên thông báo bản quyền gốc kèm URL dẫn chiếu.
4. **Quy trình thích ứng (Adaptation Workflow):**
   - Viết lại theo ngữ cảnh và thuật ngữ chuẩn của COSA (tiếng Việt nơi phù hợp).
   - Tách bạch rõ: `kept` (giữ nguyên), `changed` (sửa đổi), `added` (bổ sung governance/workspace/approval/audit) và `excluded` (loại bỏ side-effect / provider không phù hợp).
   - Đảm bảo ranh giới: Skillpack chỉ là tài liệu hướng dẫn (source reference material), không cấp quyền thực thi tự do. Mọi quyền thực thi có side-effect phải thông qua Capability được đăng ký tường minh trong composition root của COSA.

---

## 3. Mẫu Review Record

Được dán vào cuối mỗi `SKILL.md` khi hoàn thành adapt ở Part A (section `## Nguồn`):

```yaml
upstream:
  repository: coreyhaines31/marketingskills   # hoặc coreyhaines31/makerskills
  commit: <40-char SHA>
  skill: <tên skill nguồn>
  upstream_version: <metadata.version>
  license: MIT
adaptation:
  kept: [nguyên tắc/template giữ nguyên]
  changed: [path, tool, terminology, data model đã đổi]
  added: [governance, workspace, approval, audit]
  excluded: [tool/provider/side effect không nhận]
```
