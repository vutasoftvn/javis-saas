# ADR-AGENT-001: Runtime Agent Definition Naming Boundary

## Context
Codebase COSA hiện đã có model `Agent` trong `app/db/models.py`, được sử dụng cho chat personas (`name`, `slug`, `system_prompt`, `provider`, `model`) và expose qua `frontend/lib/modules/agents/`.
Spec DeepSeek Harness đề xuất một khái niệm "Agent Registry" (§7) chứa cấu hình runtime bao gồm tool permissions, model policies, và delegated subagents.

Nếu đặt tên bảng hoặc module mới là `Agent`, sẽ gây xung đột trực tiếp với domain chat persona hiện hữu và làm gãy các client REST/Flutter.

## Decision
1. Giữ nguyên model `Agent` hiện tại cho Chat Persona.
2. Định nghĩa cấu hình agent trong Agent Runtime là `RuntimeAgentProfile` / `AgentRuntimeProfile`.
3. Tách biệt rõ ràng:
   - `Agent`: Chat Persona (UI/Chat facing).
   - `RuntimeAgentProfile`: Đặc tả agent nghiệp vụ trong Agent Runtime (Tools, Policy, L0-L3 permissions).

## Consequences
- Không làm gãy API và DB schema hiện tại.
- Phân định rõ ràng trách nhiệm giữa Chat UI persona và Business Agent execution.
