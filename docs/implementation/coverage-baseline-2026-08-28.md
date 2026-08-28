# Python Test Coverage Baseline (2026-08-28)

**TPR Part:** Part 1A — Python quality gate  
**Date:** 2026-08-28  
**Measurement command:** `pytest --cov --cov-report=term-missing -m "not integration and not live_provider"`

---

## 1. Measured Baseline

| Target Package / Path | Total Statements | Missed Statements | Measured Coverage (%) | Initial Enforced Floor (`--cov-fail-under`) |
| :--- | :--- | :--- | :--- | :--- |
| `packages/agent_core` | 5,843 | 1,065 | **82%** | **80%** (measured − 2%) |
| `apps/cosa` | 3,505 | 703 | **80%** | **78%** (measured − 2%) |
| **Combined Total (Unit)** | 9,348 | 1,582 | **83%** | **80%** |

---

## 2. Coverage Ratchet Policy

1. **Fail-Closed Gate:** No PR or CI run is permitted to drop test coverage below the enforced floor for any target path.
2. **Ratchet Mechanism:**
   - As new features, tests, or bug fixes are introduced in subsequent parts (Part 1B: test coverage gaps, Part 1C: durability, Part 1D: E2E golden path), the floor will be ratcheted upward.
   - The ratchet cannot be adjusted downward without explicit approval in an architecture decision record (ADR).
3. **Exclusions:**
   - Database migrations (`*/migrations/*`)
   - Test suites and test fixtures (`*/tests/*`)
   - Legacy and virtual environment paths (`legacy/`, `.venv/`)

---

## 3. Enforcement Integration

- **Makefile targets:**
  - `agent-core-test`: `--cov=packages/agent_core --cov-fail-under=80`
  - `apps-cosa-test`: `--cov=apps/cosa --cov-fail-under=78`
  - `python-test-unit`: `--cov=packages/agent_core --cov-fail-under=80`
- **GitHub Actions CI:**
  - Job `quality-unit`: `--cov=packages/agent_core --cov-report=xml --cov-fail-under=80`
  - Job `quality-integration`: `--cov=packages/agent_core --cov=apps/cosa --cov-report=xml --cov-fail-under=80`
