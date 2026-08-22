# AI Agent OS — Specs (tách từ Master Architecture)

Theo đúng mục 104 của `markdown/AI_Agent_OS_Master_Architecture.md` ("Tài liệu tiếp theo nên tách ra khi triển khai"), 10 spec dưới đây tách phần blueprint 5600+ dòng thành từng lớp kiến trúc riêng, mỗi spec neo rõ:

- **Áp dụng cho:** `agentos/` | `legacy/agent_runtime` | cả hai — tránh đọc nhầm blueprint là mô tả trạng thái production hiện tại.
- **Trạng thái hiện tại:** tóm tắt ngắn, trỏ về `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` để biết chi tiết đầy đủ (spec không lặp lại toàn bộ gap analysis).
- **File chính:** đường dẫn code thật.
- **Còn thiếu:** gap chưa đóng, có thể trỏ tới ADR nếu cần quyết định trước khi làm.

Master document (`markdown/AI_Agent_OS_Master_Architecture.md`) vẫn là nguồn kiến trúc cấp cao — các spec này không được đi lệch khỏi nó, chỉ làm cụ thể hóa + cập nhật trạng thái theo thời gian (đúng tinh thần mục 104: "Master document vẫn là nguồn kiến trúc cấp cao để đảm bảo các spec không đi lệch khỏi kiến trúc chung").

| # | Spec | Layer |
|---|---|---|
| 01 | [agent-core-spec.md](01-agent-core-spec.md) | Agent Core & Runtime |
| 02 | [memory-spec.md](02-memory-spec.md) | Memory & Knowledge |
| 03 | [skill-spec.md](03-skill-spec.md) | Skill Ecosystem |
| 04 | [tool-mcp-spec.md](04-tool-mcp-spec.md) | Tool / MCP |
| 05 | [business-services-spec.md](05-business-services-spec.md) | Business OS / Encore |
| 06 | [workflow-event-spec.md](06-workflow-event-spec.md) | Workflow & Event |
| 07 | [governance-policy-spec.md](07-governance-policy-spec.md) | Governance & Permission |
| 08 | [evaluation-observability-spec.md](08-evaluation-observability-spec.md) | Evaluation & Observability |
| 09 | [self-improvement-spec.md](09-self-improvement-spec.md) | Self-Improvement |
| 10 | [deployment-infrastructure-spec.md](10-deployment-infrastructure-spec.md) | Deployment & Infrastructure |

**ADR liên quan (đặt hướng đi, xem trước khi code):** `docs/architecture/adr/ADR-012` (legacy/backend frozen), `ADR-013` (agentos/ là target, thay legacy/agent_runtime dần), `ADR-014` (PermissionLevel L0-L3A-L3 canonical), `ADR-015` (agentos/workflows/ canonical).
