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
| `operations.sop-builder` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `knowledge-ops` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Quy trình SOP và Runbook 5W2H; kiểm định 6 tiêu chí an toàn (Runbook5W2HValidator). |
| `operations.process-mapper` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `process-mapper` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Bản đồ quy trình BPMN, phân tích thời gian chu kỳ Value-Add vs Wait vs Rework, 3 quy tắc nghẽn TOC (ProcessCycleAnalyzer). |
| `operations.vendor-management` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `vendor-management` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Scorecard đối tác, vi phạm cam kết SLA bồi hoàn credit, phân loại rủi ro chuỗi cung ứng NIST SP 800-161 (VendorGovernanceCalculator). |
| `operations.capacity-planner` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `capacity-planner` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Định biên nhân sự vận hành/CS toán hàng đợi Erlang-C, cảnh báo kiệt sức utilization > 85%, hiring sequencer 12WY (WorkforceCapacityModeler). |
| `finance.procurement-optimizer` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `procurement-optimizer` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Tối ưu hóa chi tiêu mua sắm SaaS, chuẩn UNSPSC, phân tích Pareto 80/20, phát hiện công cụ trùng lặp (ProcurementSpendAnalyzer). |
| `people.internal-comms` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `internal-comms` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Truyền thông thay đổi nội bộ tái cơ cấu/đổi chính sách theo khung ADKAR và Kotter 8-step, kịch bản Q&A. |
| `operations.loop-lifecycle` | D | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `loop-library` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Vòng lặp phản hồi tự hành có giới hạn, 5 chế độ Discover/Find/Audit/Adapt/Design, 6 bước chu trình, 6 terminal states. |
| `marketing.aeo` | E | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `marketing-skill/skills/aeo` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Tối ưu hóa tìm kiếm ngôn ngữ lớn (Perplexity, ChatGPT, Claude) E-E-A-T, Fact-First Lede. |
| `marketing.marketing-council` | E | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `marketing-council` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Hội đồng cố vấn tiếp thị đa quan điểm; bắt buộc có Designated Dissenter. |
| `marketing.linkedin-presence` | E | `sergebulaev/linkedin-skills` | `baa9c909916f98764828e15e7cfc9dffa1aaadb1` | `skills/linkedin-post-writer` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Hiện diện LinkedIn hữu cơ chuyên nghiệp, 20 Hook Formulas, 10 Founder Angles, luật nghiệm thuật toán 2026, Thẻ Phê Duyệt Approval Card. |
| `marketing.content-humanizer` | E | `sergebulaev/linkedin-skills` | `baa9c909916f98764828e15e7cfc9dffa1aaadb1` | `skills/linkedin-humanizer` | `3.0.0` | MIT | `adapted` | `2026-09-19` | Thanh lọc văn phong AI Humanizer V3, đo mật độ theo đoạn, triệt tiêu staccato và bảo vệ chống over-correction. |
| `marketing.founder-story-bank` | E | `sergebulaev/linkedin-skills` | `baa9c909916f98764828e15e7cfc9dffa1aaadb1` | `skills/linkedin-interviewer` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Phỏng vấn chuyên sâu xây dựng Story Bank (Receipts, Turning Points, Scars, Positions, Off-limits) cho Founder. |
| `marketing.linkedin-engagement-ops` | E | `sergebulaev/linkedin-skills` | `baa9c909916f98764828e15e7cfc9dffa1aaadb1` | `skills/linkedin-reply-handler` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Tác nghiệp tương tác hữu cơ, cửa sổ động lực 60-90 phút, phản hồi 2 tầng và phân loại ICP Engagers. |
| `marketing.showcase-page-generator` | E | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `marketing/landing` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Sinh trang 3D tương tác dạng single-file HTML trong Sandbox cô lập; tuyệt đối cấm đụng vào landing/ của COSA. |
| `marketing.marketing-loops` | E | `coreyhaines31/marketingskills` | `b1aaa3619e747f4a836c61e03084c4a531de1262` | `marketing-loops` | `1.2.0` | MIT | `adapted` | `2026-09-19` | Vòng lặp tiếp thị định kỳ 9 phần giải phẫu, tích hợp với 6 Terminal States của COSA Workflow Engine. |
| `research.market-sizing` | F | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `research-ops/skills/market-research` | `2.9.0` | MIT | `adapted` | `2026-09-19` | Tính TAM/SAM/SOM kép Top-down & Bottoms-up, đo độ lệch tam giác (MarketSizingTriangulator) và cỡ mẫu Cochran (SurveySamplePlanner). |
| `research.industry-trends` | F | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `research/skills/pulse` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Đo xung lực thị trường Market Pulse đa kênh qua 5 góc nhìn phân tích và cửa sổ thời gian recency 7-90 ngày. |
| `research.dossier` | F | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `research/skills/dossier` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Thẩm định thực thể ra quyết định, kiểm chứng giả thuyết, tỷ lệ phản biện >= 30% (DisconfirmingEvidenceChecker), phân tầng nguồn (SourceTierClassifier). |
| `product.research-ops` | F | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `research-ops/skills/product-research` | `2.9.0` | MIT | `adapted` | `2026-09-19` | Cỡ mẫu bão hòa Nielsen/Guest (ResearchSaturationModeler), kho lưu trữ Observation -> Insight -> Recommendation, linter chống quy chụp 1 user. |
| `finance.rd-accounting` | F | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `research-ops/skills/research-finance` | `2.9.0` | MIT | `adapted` | `2026-09-19` | Quản trị chi phí R&D phần mềm SaaS, 6 tiêu chí IAS 38 / ASC 350-40, định tuyến đích danh R&D Finance Controller (RDCapexOpexRouter). |
| `research.patent-intelligence` | F | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `research/skills/patent` | `1.0.0` | MIT | `adapted` | `2026-09-19` | Tình báo sáng chế Prior Art, FTO và phân loại CPC kèm tuyên bố miễn trừ tư vấn pháp lý bắt buộc. |
| `executive.cto-advisor` | G | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `agents/personas/startup-cto.md & c-level-advisor/skills/cto-advisor` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Khung lãnh đạo kỹ thuật thích ứng giai đoạn (Mode A: Startup CTO thực dụng P0-P2 vs Mode B: Enterprise CTO P3-P6); cẩm nang rà soát kỹ thuật 30 phút Due Diligence. |
| `growth.bootstrapped-engine` | G | `alirezarezvani/claude-skills` | `19392f7a08264ed00486a251f5b2098321771f94` | `agents/personas/growth-marketer.md` | `2.8.0` | MIT | `adapted` | `2026-09-19` | Cỗ máy tăng trưởng tự thân $0-$1M ARR: 90-Day Compounding Content Engine, Launch Sequencer Product Hunt/HN, Conversion Drop-off Audit, CAC < 1/3 LTV. |
| `product.prd` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/artifacts-delivery.md & templates/prd.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | PRD 10 mục chuẩn hoá, Framing Gate chặn solution smuggling, tiêu chí nghiệm thu đo lường được (baseline -> target -> timeframe) và ranh giới Out of Scope. |
| `product.user-story-and-acceptance` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/artifacts-delivery.md & templates/user-story.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | Phân rã story theo lát cắt dọc (Vertical Slicing), 8 kỹ thuật xẻ nhỏ câu chuyện, cấm chia ngang theo tầng hệ thống, Gherkin Given-When-Then chuẩn QA. |
| `product.backlog-prioritization` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/strategy-positioning.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | Ma trận lựa chọn khung ưu tiên theo giai đoạn vòng đời (ICE cho Pre-PMF, RICE cho Early PMF, Kano cho Mature), quy tắc đánh đổi minh bạch, cấm HiPPO. |
| `executive.cpo-advisor` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/career-leadership.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | Nâng cấp tư duy CPO sang ngôn ngữ P&L kinh doanh, Khung 3P (Product, Practice, People), Cascading Context Map và 5 câu hỏi phỏng vấn CEO. |
| `ai.ai-product-craft` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/ai-product-craft.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | Khung năng lực AI-Shaped, Context Engineering (ngăn context rot qua chu trình Research-Plan-Reset-Implement), 5 loại PoL Probes cho AI và cẩm nang xử lý lỗi Hallucination/Latency. |
| `growth.plg-activation` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/growth-plg.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | 4 bước tìm kiếm Activation Event (Aha Moment), chẩn đoán điểm rơi phễu Onboarding 4 tầng, thiết kế Viral Loop K-factor và tối ưu chuyển đổi Freemium. |
| `finance.saas-metrics-diagnostic` | H | `Digidai/product-manager-skills` | `ab7a40662c8455ece631834dee9670b3322f465b` | `knowledge/finance-metrics.md & templates/business-health-scorecard.md` | `0.5.0` | MIT | `adapted` | `2026-09-19` | Bảng chẩn đoán sức khỏe SaaS 4 chiều, Churn kép 1-(1-r)^12, LTV:CAC vs Payback, phân tích ROI tính năng và phát hiện cạm bẫy Vanity/Blended metrics. |


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
