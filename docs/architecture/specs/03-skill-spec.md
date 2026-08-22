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

## ⚠️ Lỗ hổng an toàn xác nhận (ưu tiên cao)

`SkillRegistry.discover()` (`agentos/skills/registry.py:35-47`) đọc trực tiếp `**/manifest.yaml` từ filesystem và đánh dấu ACTIVE **ngay lập tức** — **không gọi** `supply_chain/pipeline.py`. Pipeline scan/eval/approval (`agentos/skills/supply_chain/pipeline.py:21-70`) chạy được nhưng chỉ dùng cho EXTERNAL skill candidate, chưa từng áp dụng cho skill nội bộ trong `skillpacks/`. Nghĩa là mọi skill nội bộ hiện bỏ qua toàn bộ static/security scan mà Phụ lục A §13–§14 yêu cầu bắt buộc trước khi ACTIVE.

**Đây là việc nên làm trước khi mở rộng thêm skillpacks mới**, không chỉ là tính năng "nice to have".

## Còn thiếu

- Wire `SkillRegistry.discover()` qua `supply_chain/pipeline.py` (ít nhất bước static scan) trước khi đánh dấu ACTIVE, kể cả skill nội bộ.
- Skill Review/Curator/Eval Agent (Phụ lục A §45–§47) — blueprint tự ghi "optional specialist", chưa cần làm trừ khi có nhu cầu cụ thể.
- Skill Eval (đo lường success rate/eval_score thật cho từng skill) — chưa có, khác với Agent/Workflow Eval đã có ở `agentos/evals/` (xem spec 08).

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A5.
