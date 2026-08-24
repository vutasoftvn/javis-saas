# Recipe: Research & Synthesize

- **ID:** `research.research-synthesize`
- **Domain:** research
- **Pattern:** research-synthesize (Blueprint V2 §70)
- **Nguồn:** `packages/agent_recipes/research/research-synthesize/`

## Mục đích

Pattern nền tảng: thu thập từ nhiều nguồn song song, tổng hợp thành tài liệu có cấu trúc với evidence trích dẫn cho từng nhận định. `competitor-intelligence` là 1 chuyên biệt hoá domain sales của pattern này.

## Khi nào dùng

Làm base pattern khi tạo recipe research domain khác (finance, legal, product) — kế thừa `workflow.pattern: research-synthesize`, đổi `requires.capabilities`/`requires.skills`.

## Phụ thuộc (trạng thái 2026-08-24)

`web.search` chưa implement; skill `evidence-synthesis` đã có trong `skillpacks/strategy/`.

## Governance

Read-only, không cần approval.
