# Recipe: Self-Improving Skill

Đóng gói `SkillOptimizationLab` (Wave 5-6, `packages/agent/skills/lab/`) thành recipe có thể instantiate. `mutation_fn`/`score_fn` PHẢI được tiêm thật khi dùng recipe này (bản mặc định `noop_mutator`/`default_score_fn` chỉ để test — production cần LLM-based mutator/scorer thật).

## Trạng thái phụ thuộc (2026-08-24)

`packages/agent/skills/lab/` đã có đầy đủ và test pass (`packages/agent_testkit`... thực ra ở `tests/agent/registry/test_skill_optimization_lab.py`, xem Wave 5-6). Recipe này không thêm code mới — chỉ đóng gói cách gọi.
