# Hermes/LangGraph Integration — Phase Index

> Thư mục này triển khai chi tiết từng phase của `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` (đặt tại root repo), hợp nhất `COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md` vào roadmap 11-phase của `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`.
>
> **Thứ tự authority khi có xung đột:** ADR mới hơn > `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` > `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` > `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` > code truth > `COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md` gốc.
>
> Mỗi file phase dưới đây là **bản triển khai đầy đủ** (không phải tóm tắt): giữ nguyên "Việc cụ thể" + DoD gốc từ Promotion Plan, cộng thêm phần "Bổ sung Hermes/LangGraph" đã được sequencing lại đúng vị trí (xem lý do trong Integration Plan §0 — Executive Decision, và §5 — Explicit Rejections).

## Danh sách phase

| Phase | File | Trọng tâm gốc (Promotion Plan) | Bổ sung Hermes/LangGraph |
|---|---|---|---|
| 0 | [phase-00-inventory-salvage.md](phase-00-inventory-salvage.md) | Architecture freeze + Asset Inventory & Salvage | Audit 4 file legacy context; LangGraph research-only |
| 1 | [phase-01-contracts-workflow-engine.md](phase-01-contracts-workflow-engine.md) | VNext contracts + migrate WorkflowEngine | Contract tối thiểu ContextSnapshot/CapabilityReadiness; ADR-KERNEL |
| 2 | [phase-02-durable-run-substrate.md](phase-02-durable-run-substrate.md) | Durable Run substrate (5 bảng canonical) | Không đổi — LangGraph checkpoint column hoãn tới sau gate |
| 3 | [phase-03-kernel-coordination.md](phase-03-kernel-coordination.md) | OpenAI Agents Kernel + Coordination primitives | LangGraph technical spike (isolated branch), ratify ADR-KERNEL |
| 4 | [phase-04-capability-gateway.md](phase-04-capability-gateway.md) | Capability Layer & invocation identity | CapabilityReadiness minimum enforcement; LangGraph ToolStep integration |
| 5 | [phase-05-durable-approval.md](phase-05-durable-approval.md) | Durable approval | Chứng minh LangGraph `interrupt()` không thay approval authority |
| 6 | [phase-06-drift-suite-langgraph-gate.md](phase-06-drift-suite-langgraph-gate.md) | Spec-drift & governance-drift test suite | **LangGraph adoption decision gate** (HL-01→HL-18), ADR-LANGGRAPH đóng |
| 7 | [phase-07-compose-apps-cosa.md](phase-07-compose-apps-cosa.md) | Compose `apps/cosa/` | `context_assembler.py` thật, salvage invariant từ Phase 0 |
| 8 | [phase-08-text-chat-vertical-slice.md](phase-08-text-chat-vertical-slice.md) | Vertical Slice Text Chat | `ConversationHistoryPort` contract + stub |
| 9 | [phase-09-p1-hardening.md](phase-09-p1-hardening.md) | P1 hardening (WaitDescriptor, memory/knowledge, evals...) | Context full impl, DelegationEnvelope, Readiness full, SkillSpec publication, hard-deny, LangGraph full engineering (nếu Adopt) |
| 10 | [phase-10-p2-trigger-based.md](phase-10-p2-trigger-based.md) | P2 hardening/scale, trigger-based | ADR-SKILL-IDENTITY, plugin trust, rich delegation UX, advanced LangGraph |
| 11 | [phase-11-archive.md](phase-11-archive.md) | Archive `agentos/` | DoD mở rộng +5/+6 tiêu chí Hermes/LangGraph |

## Ba ADR bắt buộc theo dõi xuyên suốt

- **ADR-KERNEL** — mở/ratify ở Phase 1, thực thi ở Phase 3.
- **ADR-LANGGRAPH** — mở ở Phase 3 (spike), đóng ở Phase 6 (adoption decision).
- **ADR-SKILL-IDENTITY** — trigger-based, dự kiến Phase 10.

## Cách dùng thư mục này

- Đọc theo thứ tự phase khi thực thi — không nhảy cóc (mỗi phase có "Điều kiện tiên quyết" tham chiếu DoD phase trước).
- Trước khi sửa `packages/agent/` hoặc `apps/cosa/` cho một phase cụ thể, đọc đúng file phase đó — đúng tinh thần CLAUDE.md ("đọc phase tương ứng trong Plan").
- Khi một phase hoàn thành, tick DoD trong chính file phase đó (không cần tạo file trạng thái riêng) và cập nhật `docs/architecture/agentos_salvage_inventory.md` nếu phase có mục liên quan salvage.
