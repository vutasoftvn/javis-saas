# Recipe: Mixture of Agents

- **ID:** `core.mixture-of-agents`
- **Domain:** core
- **Pattern:** mixture-of-agents (Blueprint V2 §70)
- **Nguồn:** `packages/agent_recipes/core/mixture-of-agents/`

## Mục đích

N agent (spec/model khác nhau) trả lời cùng 1 câu hỏi độc lập song song, 1 aggregator agent chọn/kết hợp câu trả lời tốt nhất — tăng chất lượng qua đa dạng góc nhìn, khác `advisor-orchestrator-worker` (chia nhỏ công việc khác nhau).

## Phụ thuộc

`packages/agent/coordination/parallel.py` (đã có). Chưa có ví dụ aggregator prompt/tiêu chí chọn câu trả lời cụ thể — để lại cho use case sản phẩm cụ thể.

## Governance

Read-only, không cần approval.
