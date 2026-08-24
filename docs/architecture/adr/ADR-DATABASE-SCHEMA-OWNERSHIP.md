# ADR-DATABASE-SCHEMA-OWNERSHIP: Sở hữu schema Postgres theo package, không schema chung

- **Trạng thái:** ACCEPTED — phản ánh trạng thái thật sau Wave 0-11 (2026-08-24)
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §15
  - `packages/agent_core/migrations/`, `services/cosa/migrations/`

---

## 1. Quyết định

Mỗi schema Postgres có ĐÚNG 1 package sở hữu, không package nào SQL trực tiếp vào schema của package khác (chỉ đọc qua contract/RPC/repository do package đó export):

| Schema | Sở hữu bởi | Migration | Trạng thái (2026-08-24) |
|---|---|---|---|
| `agent_core` | `packages/agent_core/runs/` | 001, 004, 005 | Composite `(run_id, tool_call_id)` PK, atomic idempotency claims |
| `agent_core_governance` | `packages/agent_core/governance/` | 002 | `GovernanceStateStore` giờ dùng đúng bởi Gateway (trước Wave 11 chỉ workflows dùng) |
| `agent_conversation` | `packages/agent_core/conversations/` | 006 | Thay hoàn toàn in-memory globals ở `apps/cosa/api/routes.py` |
| `agent_registry` | `packages/agent_core/registry/` | 007 | Dùng CHUNG cho cả AgentSpec (`spec_kind="agent"`) và SkillSpec (`spec_kind="skill"`) — không tách bảng riêng cho skill |
| `agent_evals` | `packages/agent_core/skills/lab/` (ledger, chưa có Python repository wiring) | 008 | Chỉ SQL, Python vẫn dùng model in-memory (`SkillCandidateRecord`) — persistence Postgres để lại |
| `agent_memory` | `packages/agent_core/memory/` | 003, 009 | Generic scope/provenance/lifecycle + `memory_embeddings` (trước đây không có embedding nào) |
| `knowledge` | `packages/agent_core/knowledge/` | 003, 010 | `PostgresKnowledgeStore` mới hoàn toàn (trước Wave 8 chỉ có schema, không có code Postgres nào) |
| `control_plane` | `services/cosa` (TypeScript/Encore) | services/cosa/migrations 6-9 | Port từ Python in-memory `leases.py`/`scheduler.py` — KHÔNG có consumer production hiện tại, CHƯA verify Postgres/Encore CLI thật |
| `cosa` | `services/cosa` (TypeScript/Encore) | services/cosa/migrations 1-5 | Identity/license — không đổi trong phiên này |

## 2. Quy tắc bắt buộc (không đổi từ Blueprint V2 §15)

1. `agent_core` (Python) KHÔNG được SQL trực tiếp vào business schema của `services/company`/`services/cosa`.
2. `services/cosa` (TypeScript) KHÔNG được SQL trực tiếp vào `agent_core.*`/`agent_memory.*`/... (Python schema) — giao tiếp qua HTTP internal RPC nếu cần (Wave 7 H.3, `HttpControlPlaneLeaseClient`).
3. Migration mới trong 1 schema chỉ do package sở hữu schema đó viết — không migration nào tạo bảng "tạm" trong schema của package khác.

## 3. Phát hiện quan trọng ghi lại ở đây

- **`agent_registry` dùng chung cho Agent + Skill** là quyết định thực tế (không phải kế hoạch ban đầu) — tránh tạo `skill_registry` riêng như Blueprint V2 §25 gợi ý ban đầu, xem `ADR-SKILL-IDENTITY-trigger-based-evaluation.md` §4.
- **`agent_evals` (migration 008) có schema SQL nhưng CHƯA có Python repository** — đây là 1 mẫu đã lặp lại nhiều lần trong audit phiên này (schema tồn tại, code không dùng): `knowledge.*` (trước Wave 8), `agent_memory.*` field packed (trước Wave 8), và giờ là `agent_evals.*`. Ghi lại rõ để KHÔNG lặp lại giả định "vì có migration nên chắc có code dùng".
