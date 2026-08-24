# Evals

## 1. Mục đích

2 tầng eval riêng biệt, không trùng nhau:
1. `packages/agent_core/evals/{models,runner}.py` — `CanonicalEvalRunner`, 4 nhóm eval nền tảng (kernel capability, business correctness, durability/recovery, security/governance), chạy in-memory, tồn tại từ trước phiên này.
2. `agent_evals.*` (schema Postgres, migration `008_agent_evals.sql`) + `packages/agent_core/skills/lab/` — eval CASE cho Skill Optimization Lab (Wave 5-6), dùng `EvalCase`/`score_fn` riêng, KHÔNG dùng `CanonicalEvalRunner`.

## 2. Khi nào sử dụng

`CanonicalEvalRunner`: test conformance nền tảng platform. `EvalCase`+`SkillCandidateExecutor`: chấm điểm skill candidate trong Skill Optimization Lab.

## 3. Không dùng cho việc gì

`agent_evals.*` schema (suites/cases/runs/results) CHƯA có Python repository — không nhầm là đã có persistence layer sẵn sàng dùng.

## 4. Kiến trúc và luồng dữ liệu

Xem `docs/features/skill-optimization.md` cho luồng `EvalCase`. `CanonicalEvalRunner.register_case()` + `run_all()` — không đổi trong phiên này.

## 5. Public contracts/API

`agent_core.evals.{CanonicalEvalRunner, EvalTestCase, EvalResult, EvalSuiteSummary}` (nền tảng cũ). `agent_core.skills.lab.EvalCase` (mới, Wave 5-6).

## 6. Database/schema liên quan

`agent_evals.{suites,cases,runs,results,skill_candidates,skill_mutations}` (migration 008) — SQL tồn tại, chưa có code Postgres dùng.

## 7-16.

Việc tồn đọng lớn nhất: viết `PostgresEvalsRepository` để `SkillOptimizationLab` persist `SkillCandidateRecord`/`SkillMutationRecord` thay vì chỉ giữ trong RAM của 1 process — chưa làm trong phiên Wave 0-11 (quyết định thu hẹp phạm vi có ghi chú trong `docs/features/skill-optimization.md` §14).
