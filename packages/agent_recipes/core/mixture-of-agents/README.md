# Recipe: Mixture of Agents

Pattern `mixture-of-agents` (Blueprint V2 §70) — dùng `packages/agent/coordination/parallel.py` (đã có) để chạy N agent song song cùng input, rồi 1 aggregator agent tổng hợp.

## Trạng thái phụ thuộc (2026-08-24)

Chưa có ví dụ instantiate thật (aggregator prompt cụ thể, tiêu chí chọn câu trả lời tốt nhất) — để lại cho lúc có use case sản phẩm cụ thể cần pattern này, tránh thiết kế prompt aggregator mà chưa có domain cụ thể để đánh giá chất lượng.
