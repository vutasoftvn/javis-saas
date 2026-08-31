# Evals & Benchmarks Suite

Thư mục này lưu dataset, test suite và benchmark cho model, agent, skill,
workflow và business outcome. Mỗi built-in skillpack phải sở hữu đúng một
policy-evaluation suite được khai báo bằng `quality.eval_suite` trong manifest.

## Skill evaluation contract

Mỗi `evals/<domain>/<skill>.yaml` sử dụng schema tối thiểu:

```yaml
apiVersion: cosa.ai/skill-eval/v1
kind: SkillEvalSuite
skill:
  id: operations.tasks
  version: 2.0.0
cases:
  - id: accepts-governed-context
    input:
      workspace_id: ws-eval
      project_id: project-eval
    expected:
      outcome: accept
  - id: cross-workspace
    input:
      workspace_id: ws-other
      project_id: project-eval
    expected:
      outcome: reject
      reason: cross-workspace
```

Validation command:

```bash
make skillpacks-validate
PYTHONPATH=packages:. python -m pytest tests/agent/skills/test_skillpack_eval_contract.py -q
```

Suite YAML chứng minh ownership, phiên bản, và policy case coverage. Nó **không**
phải bằng chứng rằng LLM behavioural evaluation đã được chạy hoặc đạt điểm; kết
quả thực thi phải được ghi qua runtime evaluation có audit riêng.
