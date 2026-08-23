# COSA Canonical Ownership Map

> **Status:** Fully Promoted Canonical Architecture (Promotion Completed — Phases 0–11 Completed)  
> **Update 2026-08-23:** Identity/workforce storage section below was revised by `docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md` — see that spec for the current `core`/`workforce` schema and ownership boundary.  
> **Date:** 2026-08-23  
> **Authority:** Tài liệu này là căn cứ phân định quyền sở hữu (ownership authority) cho toàn bộ hệ thống COSA. Phản ánh trực tiếp kết quả triển khai từ Master Guide M1 (`COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`) và Promotion Plan (`COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`).  
> **Cross-reference:** `docs/architecture/agentos_salvage_inventory.md` (Bảng kiểm kê tài sản và thu hồi chi tiết).

---

## 1. Classification Vocabulary

- **Canonical Target Owner:** Kiến trúc đích chính quy đã hoàn thiện (`packages/agent_core/`, `apps/cosa/`, `services/*`).
- **Archived Legacy Systems:** Mã nguồn lịch sử đã hoàn thành thu hồi tài sản và được archive (`legacy/agent_runtime_archive/`, `legacy/backend/`, `legacy/agent_runtime/`).
- **Active Business Service:** Dịch vụ nghiệp vụ đang hoạt động thực tế trên nền tảng Encore (`services/company/*`, `services/cosa/*`).

---

## 2. Canonical Ownership Map (Mục tiêu đã hoàn tất)

| Capability / Subsystem | Canonical Owner | Origin / Transition Source | Operational Status |
|---|---|---|---|
| **Core Contracts & Identities** | `packages/agent_core/contracts/` | Master Guide §6–§8, §16, §19 | Canonical Live Contract |
| **Workflow Engine & DAG** | `packages/agent_core/workflows/` | Promoted from `agentos/workflows/*` (Phase 1) | Canonical Live Engine |
| **Governance & Policy** | `packages/agent_core/governance/` | Promoted & Hardened (Phase 1, 6, 10) | Canonical Live Governance |
| **Durable Run Substrate** | `packages/agent_core/runs/` (5 bảng `agent_core.*`) | Master Guide §11–§12 (Phase 2) | Canonical Live Substrate |
| **Execution Kernel** | `packages/agent_core/kernel/` | OpenAI Agents SDK (`OpenAIAgentsKernel`, Phase 3) | Canonical Live Kernel |
| **Coordination Primitives** | `packages/agent_core/coordination/` | 7 Primitives & WaitResolver (Phase 3, 9) | Canonical Live Coordination |
| **Capability Gateway** | `packages/agent_core/capabilities/` | Gateway & Invocation Identity (Phase 4) | Canonical Live Gateway |
| **Durable Approvals** | `packages/agent_core/capabilities/approval_service.py` | Fresh Governance Validation (Phase 5) | Canonical Live Approvals |
| **COSA Composition Root** | `apps/cosa/composition/` | `build_cosa_agent_plane()`, `context_assembler.py` (Phase 7) | Canonical Live App Plane |
| **Context & Conversation History** | `apps/cosa/conversations/`, `contracts/context.py` | ConversationRepository (HL-03), ContextSnapshot (Phase 8, 9) | Canonical Live Context & History |
| **Delegation Envelope & Authority** | `packages/agent_core/coordination/delegation_envelope.py` | Authority Attenuation (HL-06, HL-07) (Phase 9) | Canonical Live Delegation |
| **Skill Registry & Publication** | `packages/agent_core/skills/` | Immutable SkillSpec (HL-04, HL-05) (Phase 9) | Canonical Live Skill Registry |
| **COSA Agent API** | `apps/cosa/api/` | SSE Streaming & REST Endpoints (Phase 8) | Canonical Live API |
| **Memory Subsystem** | `packages/agent_core/memory/` | Promoted from `agentos/memory/*` (Phase 9) | Canonical Live Memory |
| **Company Knowledge & RAG** | `packages/agent_core/knowledge/` | Promoted from `agentos/knowledge/*` (Phase 9) | Canonical Live Knowledge |
| **Evaluation & Benchmarks** | `packages/agent_core/evals/` | Promoted from `agentos/evals/*` (Phase 9) | Canonical Live Evals |
| **Plugins & Extensions** | `packages/agent_core/plugins/` | PluginManifest & Registry (Phase 10) | Canonical Live Plugins |
| **Artifact Lifecycle & Distribution** | `packages/agent_core/artifacts/` | Multi-Backend Lifecycle (Phase 9, 10) | Canonical Live Artifacts |
| **Business Domain Services** | `services/company/`, `services/cosa/` | Encore Microservices | Active Canonical Business Services |
| **Hybrid Workforce Identity** | `services/company/identity` (`core.workforce_members`) | Encore Identity Module (part of `services/company`) | Active Canonical Identity Source |
| **Flutter Chat UI** | `frontend/lib/modules/chat/` | Clean Integration with `apps/cosa/api/` (Phase 8) | Active Chat UI |
| **Legacy Systems (Archive)** | `legacy/agent_runtime_archive/` | Archived from `agentos/` (Phase 11) | **Frozen Archive** |

---

## 3. Storage & Database Schema Ownership

Toàn bộ hệ thống chạy trên PostgreSQL cluster với các schema được phân tách trách nhiệm tuyệt đối:

1. **`agent_core` (Canonical Agent Substrate):**
   - Sở hữu bởi: `packages/agent_core/runs/`
   - Bảng: `agent_core.runs`, `agent_core.run_checkpoints`, `agent_core.run_events`, `agent_core.run_tool_calls`, `agent_core.approvals`.
2. **`agent_memory` (Agent Long-term Memory):**
   - Sở hữu bởi: `packages/agent_core/memory/`
   - Bảng: `agent_memory.agent_memories`.
3. **`knowledge` (Company Document Chunks & PgVector):**
   - Sở hữu bởi: `packages/agent_core/knowledge/`
   - Bảng: `knowledge.knowledge_sources`, `knowledge.knowledge_chunks`.
4. **Business Schemas (`operating`, `commercial`, `identity`, `finance_legal`, `control_plane`):**
   - Sở hữu duy nhất bởi các microservice trong `services/company/` và `services/cosa/` (Encore + Drizzle ORM).
   - **Ranh giới tuyệt đối:** `packages/agent_core/` cấm không được kết nối hoặc import trực tiếp bất kỳ schema nghiệp vụ nào.

---

## 4. Quy tắc phát triển mã nguồn (Rules for Code Contribution)

1. **Ranh giới gói `packages/agent_core/`:**
   - Là thư viện lõi độc lập domain, có thể tái sử dụng cho ứng dụng khác.
   - Tuyệt đối cấm import bất kỳ file nào từ `services/company/*` hoặc `services/cosa/*` hoặc `apps/*`.
2. **Ranh giới ứng dụng `apps/cosa/`:**
   - Là nơi duy nhất kết nối các capability của `packages/agent_core/` với các business RPC/API của `services/company/`.
3. **Lưu trữ lịch sử `legacy/agent_runtime_archive/`:**
   - Đã đóng băng vĩnh viễn và lưu trữ cho mục đích tham khảo lịch sử git.
