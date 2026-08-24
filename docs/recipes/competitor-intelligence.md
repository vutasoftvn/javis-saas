# Recipe: Competitor Intelligence

- **ID:** `sales.competitor-intelligence`
- **Domain:** sales
- **Pattern:** research-synthesize (Blueprint V2 §70)
- **Nguồn:** `packages/agent_recipes/sales/competitor-intelligence/`

## Mục đích

Tổng hợp thông tin công khai về đối thủ cạnh tranh thành báo cáo có trích dẫn nguồn, dùng cho sales/marketing ra quyết định định vị sản phẩm.

## Khi nào dùng

Khi cần đánh giá nhanh 1 đối thủ cụ thể (tính năng, giá, positioning) từ nguồn công khai — không thay thế nghiên cứu thị trường sâu có trả phí.

## Không dùng cho việc gì

Không dùng để lấy dữ liệu nội bộ/bảo mật của đối thủ, không dùng làm nguồn duy nhất cho quyết định đầu tư/pháp lý.

## Phụ thuộc (trạng thái 2026-08-24)

- `web.search` capability — **chưa implement**.
- Skill `skillpacks/strategy/evidence-synthesis` — đã có.

## Governance

Read-only, không cần approval. Output là artifact `report`, không tự động gửi ra ngoài.
