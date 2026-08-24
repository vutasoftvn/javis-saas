# Recipe: Dependency Doctor

- **ID:** `dev.dependency-doctor`
- **Domain:** dev
- **Pattern:** critic-revise (Blueprint V2 §70)
- **Nguồn:** `packages/agent_recipes/dev/dependency-doctor/`

## Mục đích

Phát hiện dependency lỗi thời/có lỗ hổng bảo mật, đề xuất bản vá kèm đánh giá rủi ro breaking change.

## Deterministic vs Agentic Boundary

Quét dependency + tra cứu CVE database = deterministic code. LLM chỉ dùng ở bước đọc changelog và tự phê bình đề xuất (critic-revise: 1 lượt đề xuất, 1 lượt tự phê bình trước khi chốt).

## Phụ thuộc (trạng thái 2026-08-24)

`web.search` chưa implement; nguồn CVE database cụ thể chưa quyết định.

## Governance

Read-only (chỉ đề xuất, không tự apply bản vá) — approval cần cho bước RIÊNG BIỆT "apply patch", không nằm trong phạm vi recipe này.
