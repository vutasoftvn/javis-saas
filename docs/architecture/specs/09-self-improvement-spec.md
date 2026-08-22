# 09 — Self-Improvement Spec

**Blueprint gốc:** §34–§37, §90, §94–§97, Phụ lục A §20/§40–§52 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** chỉ `agentos/` — `legacy/agent_runtime` không có khái niệm improvement loop.

## Trạng thái hiện tại

Layer build đầy đủ nhất và trung thành nhất với blueprint:

| Thành phần | File |
|---|---|
| Capability gap detection | `agentos/improvement/gap_detection.py` (`GapDetector`) |
| Skill distillation | `agentos/improvement/distillation.py` (`distill_skill()`) |
| Candidate proposal | `agentos/improvement/proposal.py` (`propose_candidates()`) |
| Improvement Hierarchy | `agentos/improvement/hierarchy.py` (EXECUTION → TOOL_SELECTION → SKILL_SELECTION → ... đúng thứ tự §36) |
| Human approval gate | `agentos/improvement/approval_gate.py` |

## Còn thiếu

**Toàn bộ vòng lặp self-improvement này chưa từng chạy trên dữ liệu production thật** — vì `agentos/` chưa wire vào production (ADR-AGENTOS-001, ADR-013 mới chỉ đặt hướng đi, chưa cutover). Không có gap code cụ thể nào khác được xác nhận ở layer này; việc còn lại là vận hành, không phải thiếu implementation.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A10.
