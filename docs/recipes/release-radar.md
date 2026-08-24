# Recipe: Dependency Release Radar

- **ID:** `ops.release-radar`
- **Domain:** ops
- **Pattern:** watch-rank-deliver (Blueprint V2 §70)
- **Nguồn:** `packages/agent_recipes/ops/release-radar/`

## Mục đích

Theo dõi release mới của dependency, đánh giá độ liên quan/rủi ro bằng LLM (chỉ ở bước đánh giá, không parse bằng LLM), gửi thông báo qua channel đã cấu hình.

## Deterministic vs Agentic Boundary

Parser dependency manifest + gọi GitHub release API + so sánh version = **code thường** (deterministic). LLM CHỈ dùng để đọc changelog/đánh giá độ liên quan sau khi đã có version delta xác định — đúng nguyên tắc Blueprint V2 §72 ("Không dùng LLM để parse thứ mà parser chắc chắn hơn, rẻ hơn và test được").

## Phụ thuộc (trạng thái 2026-08-24)

Dùng control-plane primitives Wave 7 (`control_plane.watches/signal_observations/delivery_policies`) — **Wave 7 chưa verify được bằng Postgres/Encore CLI thật**, recipe này ở trạng thái thiết kế. Parser manifest cụ thể chưa viết.

## Governance

Gửi thông báo ra ngoài (Slack/email/webhook) — side effect class `external-notification`, không cần approval per-run nhưng cấu hình delivery policy nên qua review.
