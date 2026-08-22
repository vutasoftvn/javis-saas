# 03 — Skill Ecosystem Spec

**Blueprint gốc:** §18–§37 + toàn bộ Phụ lục A (63 mục) của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** chỉ `agentos/` — `legacy/agent_runtime` không có khái niệm Skill/SKILL.md nào.

## Trạng thái hiện tại

Đây là layer hiện thực hóa đầy đủ nhất so với blueprint:

| Thành phần | File |
|---|---|
| Registry | `agentos/skills/registry.py` (discovery qua `manifest.yaml`) |
| Router | `agentos/skills/router.py` (scoring relevance/trust/quality) |
| Loader (progressive disclosure) | `agentos/skills/loader.py`, `instruction_loader.py` |
| Canonical manifest | `agentos/skills/manifest.py` |
| Supply chain | `agentos/skills/supply_chain/` (pipeline.py, artifact_store.py, pinning.py, scan.py, lifecycle.py) |

Skillpacks thật: `skillpacks/{tasks,okr,twelve-week-year,marketing/*,core/weekly-review}/`.

## Internal skill bypass supply chain — cố tình, đúng thiết kế (đã xác minh)

`SkillRegistry.discover()` (`agentos/skills/registry.py:35-47`) đọc trực tiếp `**/manifest.yaml` và đánh dấu ACTIVE ngay, không gọi `supply_chain/pipeline.py`. Ban đầu bản phân tích ghi nhầm đây là "lỗ hổng an toàn" — **đã sửa lại sau khi đọc kỹ hơn**: docstring của cả `SkillRegistry` lẫn `SupplyChainPipeline` đều nói rõ pipeline chỉ dành cho EXTERNAL skill; mọi `skillpacks/*/manifest.yaml` thật đều khai `trust.tier: T0`, và theo đúng bảng trust tier blueprint §29 (T0 = internal = trusted). `scan_manifest()` chỉ đánh giá rủi ro cho T3/T4 nên với skill T0, wire pipeline vào sẽ không đổi hành vi gì — hành vi hiện tại là chính xác, không cần sửa.

Pipeline này **cần được dùng khi có skill EXTERNAL đầu tiên** (theo Phụ lục A §13, T1-T4) — hiện `skillpacks/` chưa có case này nên chưa cần gọi tới `import_candidate()`/`scan()`/`stage()`/`promote_to_active()`.

## Còn thiếu

- Skill Review/Curator/Eval **Agent** (Phụ lục A §45–§47, 3 specialist agent) — blueprint tự ghi "optional specialist", chưa cần làm trừ khi có nhu cầu cụ thể. (Không nhầm với Skill **Eval** thuần túy — `agentos/evals/skill_eval.py` đã có, xem spec 08.)
- Skill Eval (đo lường success rate/eval_score thật cho từng skill) — chưa có, khác với Agent/Workflow Eval đã có ở `agentos/evals/` (xem spec 08).

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A5.
