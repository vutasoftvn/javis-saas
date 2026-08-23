# Phase 11 — Archive `agentos/`

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 11" (Step 11). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

Gỡ bỏ hoàn toàn phụ thuộc vào `agentos/` runtime cũ, chỉ giữ làm lịch sử tham khảo — với Definition of Done mở rộng để bao phủ cả track Hermes/LangGraph nếu đã kích hoạt.

## Điều kiện tiên quyết

Promotion Definition of Done (Master doc §42) pass toàn bộ 15 tiêu chí gốc **cộng** (chỉ áp dụng cho track đã kích hoạt thật) 5-6 tiêu chí bổ sung dưới đây.

## Definition of Done — 15 tiêu chí gốc (Master doc §42)

1. `packages/agent_core` owns clean contracts.
2. OpenAI Agents kernel pass model compatibility matrix.
3. Durable Run/Checkpoint/Event/ToolCall/Approval hoạt động qua restart (process thật).
4. AgentSpec/WorkflowSpec pinned bằng immutable identity.
5. Exact invocation identity tồn tại.
6. Write side effects idempotent (đã test failure window).
7. Approval sống qua restart.
8. Current governance có thể narrow nhưng không bao giờ widen invocation cũ.
9. Waiting states có routable descriptor.
10. WorkflowEngine resume durable.
11. Capability calls chạm `services/company` thật.
12. Text Chat integration dùng API mới.
13. Security/eval gates pass.
14. Không còn production path nào cần `AgentRuntime` cũ.
15. App thứ hai reuse được Agent Core mà không import COSA business.

## Definition of Done — bổ sung Hermes/LangGraph (chỉ track đã kích hoạt)

16. Context assembly hoạt động cho ≥3 intent type qua use case thật (không phải test giả lập) — chỉ áp dụng nếu Track 9A đã chạy production.
17. Delegation authority attenuation test pass, child không thể escalate quyền vượt trần parent — chỉ áp dụng nếu Track 9B (DelegationEnvelope) đã chạy production.
18. Skill publication lifecycle test pass, publish version mới không mutate/ảnh hưởng Run đang chạy dùng version cũ — chỉ áp dụng nếu Track 9D (SkillSpec) đã publish ít nhất 1 skill thật.
19. Conversation search không leak cross-tenant (HL-03) — chỉ áp dụng nếu Track 9A conversation search đã chạy production.
20. Hard non-approvable action không thể bypass dưới bất kỳ approval evidence hay autonomy level nào (HL-10) — chỉ áp dụng nếu Track 9E đã kích hoạt.
21. (Nếu ADR-LANGGRAPH = Adopt tại Phase 6) HL-01 → HL-18 pass đầy đủ trên main branch, không còn giới hạn ở branch spike.

## Việc cụ thể khi đủ điều kiện (gốc)

1. Xác nhận với người dùng trước khi archive/xóa (hành động phá hủy) — liệt kê rõ những gì sẽ archive vs xóa hẳn.
2. Di chuyển `agentos/` sang `legacy/agent_runtime_archive/` hoặc archive branch riêng (không xóa thẳng — giữ lịch sử git đã có).
3. Gỡ mọi reference còn sót trong docs/README trỏ về `agentos/` như nguồn hiện hành.
4. Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` lần cuối để đóng vòng đời `agentos/`.

## Bổ sung Hermes/LangGraph — việc cụ thể khi archive

5. Nếu branch `experiment/langgraph-spike` chưa merge (do Phase 6 quyết định Reject hoặc Defer): archive branch (không xóa) cùng đợt với `agentos/`, ghi rõ trong `docs/architecture/langgraph_spike_results.md` trạng thái cuối cùng và lý do không adopt, để tránh người sau lặp lại spike mà không đọc kết quả cũ.
6. Đóng ADR-SKILL-IDENTITY nếu vẫn còn mở ở trạng thái "chưa trigger" — ghi rõ đây là quyết định "chưa cần" chứ không phải "quên làm", để tránh future confusion về việc SkillSpec publication tồn tại nhưng execution consumption bị khóa có chủ đích.
7. Review lại toàn bộ `legacy/agent_runtime/workforce/agents/context/*` — nếu đã salvage xong theo `CONTEXT_ASSEMBLER_AUDIT.md` (Phase 0) và không còn giá trị tham chiếu thêm, có thể gộp chung đợt archive với `agentos/` (xác nhận người dùng, cùng cơ chế mục 1).

## Rủi ro/lưu ý

**Gốc:** Đây là hành động phá hủy (di chuyển/archive) cần xác nhận rõ ràng với người dùng trước khi thực hiện, không tự ý.

**Bổ sung:** Không tuyên bố Phase 11 xong nếu track nào đó (9A-9F, Phase 10 mục 8-11) đang ở trạng thái "dở dang" — hoặc hoàn thành đủ DoD của track đó, hoặc dừng lại rõ ràng bằng ADR ghi nhận "không trigger, không cần trong scope hiện tại", không được để lửng lơ không rõ trạng thái khi archive `agentos/`.
