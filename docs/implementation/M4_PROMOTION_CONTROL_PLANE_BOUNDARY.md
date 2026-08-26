# M4 — Ranh giới Promotion giữa agent_core và services/cosa

**Ngày:** 2026-08-26
**Nguồn:** Wave M4 (`docs/superpowers/plans/2026-08-26-marin-patterns-m4-promotion-evidence.md`), theo
`COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` §12.3 và CLAUDE.md
"Bốn vùng kiến trúc".

## Quyết định

`packages/agent_core/evals/` (Wave M4) sở hữu:

- `PromotionEvidence` — bằng chứng bất biến (target ref + fingerprint quan sát + eval run refs + policy check result).
- `PromotionGate.check()` — hàm THUẦN kiểm tra (stale/dependency drift/eval chưa pass), trả `PromotionGateResult`, KHÔNG side effect.
- `PromotionEvidenceRepository` — persistence CHO evidence (`agent_evals.promotion_evidence`, migration 014).

`agent_core` **KHÔNG** sở hữu và **KHÔNG BAO GIỜ** tự triển khai:

- `PromotionDecision` — bản ghi quyền quyết định "artifact X@version Y được phép chạy production" — đây là business/platform authority, thuộc `services/cosa` (đã chốt từ ADR-CONTROLPLANE-001, CLAUDE.md rule 1: "Business truth thuộc `services/*`, không thuộc LLM runtime / Agent Platform").
- Activation/deployment record — việc AgentSpec nào đang thật sự phục vụ traffic production.
- Bất kỳ code nào tự động set trạng thái "promoted"/"active" dựa trên `PromotionGateResult.approved == True` — `approved=True` chỉ là 1 input cho quyết định của `services/cosa`, không phải quyết định tự nó.

## Luồng dự kiến (services/cosa gọi vào agent_core, KHÔNG phải chiều ngược lại)

```text
services/cosa nhận yêu cầu promote (người dùng/API)
   │
   ▼
Query agent_core: PromotionEvidenceRepository.list_by_target(target_ref)
   │
   ▼
Query agent_core: PromotionGate(policy_version).check(evidence, current_fingerprints)
   │
   ├── approved == False → services/cosa từ chối, trả blocking_issues cho người dùng
   │
   └── approved == True
          │
          ▼
   services/cosa TỰ QUYẾT: ghi PromotionDecision (bảng của services/cosa, KHÔNG phải
   agent_evals.*), gọi activation logic riêng của nó — code này KHÔNG nằm trong
   agent_core, không nằm trong phạm vi Wave M4.
```

`current_fingerprints` mà `services/cosa` truyền vào `PromotionGate.check()` phải tự tính
tại thời điểm gọi (vd qua `SpecResolver.resolve_agent_spec_dependencies()`, Wave M2, để lấy
fingerprint MỚI NHẤT của target + dependency) — KHÔNG dùng lại `observed_fingerprints` đã
lưu sẵn trong evidence (đó là "lúc xưa", không phải "bây giờ") cho tham số này.

## Vì sao ranh giới này quan trọng

- **Compliance/audit**: 1 quyết định "đưa gì lên production" phải truy vết được về đúng 1
  bản ghi thuộc hệ thống ghi nhận business truth (`services/cosa`), không rải rác trong
  Python runtime state của `agent_core` (có thể restart, có nhiều instance chạy song song).
- **Không để LLM/agent runtime tự cấp quyền cho chính nó** — nếu `agent_core` tự activate
  dựa trên `PromotionGateResult`, một agent chạy trong chính runtime đó (vd Skill Optimization
  Lab) về lý thuyết có đường trực tiếp tới production mà không qua approval con người/business
  policy thật — vi phạm CLAUDE.md rule 5/8.

## Trạng thái triển khai

- `agent_core` phía (Task 1-5, Wave M4): **triển khai xong** khi plan
  `2026-08-26-marin-patterns-m4-promotion-evidence.md` hoàn tất.
- `services/cosa` phía (query evidence, ghi PromotionDecision, activation): **CHƯA triển
  khai** — không nằm trong phạm vi Marin Patterns addendum hiện tại, cần plan riêng khi có
  yêu cầu cụ thể (API nào expose evidence-query, schema PromotionDecision trong
  `services/cosa`, UI/flow người dùng bấm "promote").
