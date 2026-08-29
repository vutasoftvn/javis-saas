# Skill Optimization Lab

## 1. Mục đích

Vòng lặp Executor→Scorer→Mutator→Challenger eval→revert/keep→full regression để cải thiện skill có kiểm soát, không tự publish.

## 2. Khi nào sử dụng

Khi có skill đã publish nhưng đo được hiệu suất chưa tốt, muốn thử cải thiện với bounded rounds + holdout chống overfit.

## 3. Không dùng cho việc gì

KHÔNG tự publish skill mới vào registry chính — luôn dừng ở `SkillCandidateRecord(status="evaluated")`, chờ approval người.

## 4. Kiến trúc và luồng dữ liệu

```
SkillOptimizationLab.optimize(base_skill, cases)
  → baseline: SkillCandidateExecutor.run_suite(base_skill, cases, include_holdout=False)
  → for round in 1..max_rounds:
      mutated, rationale = mutation_fn(current_skill)
      new_score = run_suite(mutated, cases, include_holdout=False)
      if new_score > latest_score: accept, current_skill = mutated
      else: revert (giữ current_skill, thử round tiếp từ trạng thái tốt nhất đã biết)
  → full regression: run_suite(current_skill, cases, include_holdout=True)
  → status = "evaluated"
```

`SkillCandidateExecutor` chạy qua `ExecutionKernel` THẬT (không mock riêng cho lab) — nối `candidate_skill.instructions` vào `AgentSpec.instructions` tạm thời với version tag riêng mỗi round (`{base_version}-lab-{run_label}`) để tránh `SpecVersionHashConflictError` khi nội dung đổi giữa các round, và tránh làm bẩn registry chính với version throwaway.

## 5. Public contracts/API

`agent.skills.lab.{SkillOptimizationLab, SkillCandidateExecutor, EvalCase, MutationFn, ScoreFn, noop_mutator, default_score_fn}`.

## 6. Database/schema liên quan

Schema `agent_evals` (migration 008): `skill_candidates`, `skill_mutations` — **CHƯA có Python repository wiring**, hiện dùng model in-memory (`SkillCandidateRecord`/`SkillMutationRecord`) trong process, không persist.

## 7. Cấu hình

`mutation_fn`/`score_fn` PHẢI tiêm thật cho production — mặc định (`noop_mutator`/`default_score_fn`) chỉ dùng cho test.

## 8. Ví dụ sử dụng

```python
lab = SkillOptimizationLab(executor=executor, mutation_fn=my_llm_mutator, max_rounds=3)
record = await lab.optimize(base_skill, eval_cases)
if record.latest_score > threshold:
    # người duyệt xem xét record.proposed_content trước khi publish thật
    await publish_skill_spec(SkillSpec(**record.proposed_content, version="1.1.0"), repository=registry, publisher=reviewer)
```

## 9. Cách bổ sung implementation mới

Tiêm `mutation_fn: Callable[[SkillSpec], tuple[SkillSpec, str]]` và `score_fn: Callable[[RunResult, EvalCase], float]` thật (LLM-based) — không hardcode 1 chiến lược cụ thể trong hạ tầng lõi.

## 10. Security/governance

Optimization chạy read-only trên candidate copy. Publish thật luôn cần approval người — không có đường tắt.

## 11. Error handling

Không có exception riêng — lỗi từ `kernel.run()` propagate qua `RunResult` bình thường, `score_fn` mặc định trả 0.0 nếu Run không COMPLETED.

## 12. Observability

Không có event riêng hiện tại (durable ledger `agent_evals.*` chưa wire).

## 13. Testing

`tests/agent/registry/test_skill_optimization_lab.py` — mock model client trả output khác nhau tuỳ system prompt có chứa keyword hay không, chứng minh vòng lặp optimize() có ý nghĩa thật (không phải giả lập điểm số).

## 14. Migration/backward compatibility

Migration 008 additive, chưa có code Postgres dùng.

## 15. Troubleshooting

`optimize()` chạy chậm/tốn cost: `max_rounds` là giới hạn duy nhất hiện có — chưa có cost/token budget riêng (Blueprint V2 §69.3 gợi ý, chưa implement).

## 16. Definition of Done

- [x] Orchestration logic đầy đủ, invariant "không tự publish", test end-to-end qua kernel thật
- [ ] Persistence Postgres cho `SkillCandidateRecord`/`SkillMutationRecord` (hiện chỉ in-memory)
- [ ] Cost/token budget enforcement
- [ ] `mutation_fn`/`score_fn` thật (LLM-based) — hiện chỉ có default đơn giản
