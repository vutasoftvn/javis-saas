# Recipe: Advisor-Orchestrator-Worker

- **ID:** `core.advisor-orchestrator-worker`
- **Domain:** core
- **Pattern:** supervisor-worker (Blueprint V2 §70)
- **Nguồn:** `packages/agent_recipes/core/advisor-orchestrator-worker/`

## Mục đích

1 orchestrator agent phân rã mục tiêu thành task chuyên biệt, giao cho worker agent chạy song song, tổng hợp kết quả cuối.

## Khi nào dùng

Mục tiêu phức tạp cần nhiều chuyên môn khác nhau (vd "đánh giá thương vụ M&A" cần cả phân tích tài chính + pháp lý + thị trường) — mỗi worker là 1 AgentSpec chuyên biệt.

## Phụ thuộc

Dùng trực tiếp `packages/agent_core/coordination/{supervisor,parallel,quality_gate,synthesis}.py` — **đã tồn tại từ trước phiên làm việc Blueprint V2**, không phải code mới. Recipe này chỉ tài liệu hoá cách compose.

## Governance

Phụ thuộc vào capability risk của từng worker task — không có 1 mức governance chung cho cả recipe.
