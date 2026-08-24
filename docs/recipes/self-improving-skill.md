# Recipe: Self-Improving Skill

- **ID:** `core.self-improving-skill`
- **Domain:** core
- **Pattern:** self-improving-skill (Blueprint V2 §69.3/§70)
- **Nguồn:** `packages/agent_recipes/core/self-improving-skill/`

## Mục đích

Đóng gói vòng lặp Skill Optimization Lab (Executor→Scorer→Mutator→Challenger eval→revert/keep→full regression, Wave 5-6) thành recipe instantiate được.

## Khi nào dùng

Khi có skill đã publish nhưng đo được hiệu suất chưa tốt (qua eval suite), muốn thử cải thiện có kiểm soát (bounded rounds, holdout chống overfit).

## Không dùng cho việc gì

KHÔNG tự publish skill mới — luôn dừng ở `SkillCandidateRecord(status="evaluated")`, chờ người duyệt gọi `publish_skill_spec()` riêng (ADR-SKILL-IDENTITY §4 invariant).

## Phụ thuộc

`packages/agent_core/skills/lab/` (Wave 5-6) — đã có, test pass. `mutation_fn`/`score_fn` mặc định (`noop_mutator`/`default_score_fn`) chỉ dùng cho test, production cần tiêm implementation thật.

## Governance

Optimization chạy read-only trên candidate copy. Publish thật (ngoài phạm vi recipe này) luôn cần approval người.
