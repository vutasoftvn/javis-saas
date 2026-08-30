# AI Agent OS — Specs (tách từ Master Architecture)

Theo đúng mục 104 của `markdown/AI_Agent_OS_Master_Architecture.md` ("Tài liệu tiếp theo nên tách ra khi triển khai"), 10 spec dưới đây tách phần blueprint 5600+ dòng thành từng lớp kiến trúc riêng, mỗi spec neo rõ:

- **Áp dụng cho:** `agentos/` | `legacy/agent_runtime` | cả hai — tránh đọc nhầm blueprint là mô tả trạng thái production hiện tại.
- **Trạng thái hiện tại:** tóm tắt ngắn, trỏ về `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` để biết chi tiết đầy đủ (spec không lặp lại toàn bộ gap analysis).
- **File chính:** đường dẫn code thật.
- **Còn thiếu:** gap chưa đóng, có thể trỏ tới ADR nếu cần quyết định trước khi làm.

Master document (`markdown/AI_Agent_OS_Master_Architecture.md`) vẫn là nguồn kiến trúc cấp cao — các spec này không được đi lệch khỏi nó, chỉ làm cụ thể hóa + cập nhật trạng thái theo thời gian (đúng tinh thần mục 104: "Master document vẫn là nguồn kiến trúc cấp cao để đảm bảo các spec không đi lệch khỏi kiến trúc chung").

| # | Spec | Layer |
|---|---|---|
| 01 | `01-agent-core-spec.md` (Planned) | Agent Core & Runtime |
| 02 | `02-memory-spec.md` (Planned) | Memory & Knowledge |
| 03 | `03-skill-spec.md` (Planned) | Skill Ecosystem |
| 04 | `04-tool-mcp-spec.md` (Planned) | Tool / MCP |
| 05 | `05-business-services-spec.md` (Planned) | Business OS / Encore |
| 06 | `06-workflow-event-spec.md` (Planned) | Workflow & Event |
| 07 | `07-governance-policy-spec.md` (Planned) | Governance & Permission |
| 08 | `08-evaluation-observability-spec.md` (Planned) | Evaluation & Observability |
| 09 | `09-self-improvement-spec.md` (Planned) | Self-Improvement |
| 10 | `10-deployment-infrastructure-spec.md` (Planned) | Deployment & Infrastructure |


**ADR liên quan (đặt hướng đi, xem trước khi code):** `docs/architecture/adr/ADR-012` (legacy/backend frozen), `ADR-013` (agentos/ là target, thay legacy/agent_runtime dần), `ADR-014` (PermissionLevel L0-L3A-L3 canonical), `ADR-015` (agentos/workflows/ canonical).

## AI Compliance Production Hardening Specification

- **Specification & Implementation Plan:** `docs/superpowers/plans/2026-08-30-ai-compliance-production-hardening.md`
- **Statutory Source Provenance:** `docs/architecture/specs/legal-rules-matrix.md` anchored to Vietnamese Official Gazette signed PDFs (`vb-ai/`).
- **Production Verification Gate:** `make ai-compliance-production-gate`
  - Company TypeScript Private & Governance contract tests (`vitest run finance-legal/tests/ai-compliance-*.test.ts`)
  - COSA & E2E HTTP Acceptance Tests (`pytest tests/apps/cosa/compliance tests/e2e/test_ai_compliance_company_http.py -q`)
  - Flutter Frontend Compliance Center tests (`flutter test test/modules/legal/ai_compliance_service_test.dart test/data/models/ai_compliance_models_test.dart`)

