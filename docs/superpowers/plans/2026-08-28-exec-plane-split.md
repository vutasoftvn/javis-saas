# SPEC-EXEC-PLANE-SPLIT — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. Steps use `- [ ]`.

**Goal:** Tách `COSA_CONTROL_PLANE_URL` thành `COSA_EXECUTION_PLANE_URL` (local run dispatch/lease/schedule) + `COSA_PLATFORM_CONTROL_PLANE_URL` (VPS identity/connector/policy/ingestion-control), qua một helper có fail-fast, repoint mọi call-site; legacy var chỉ còn fallback.

**Architecture:** Một module `apps/cosa/config/planes.py` với `resolve_execution_plane_url()` / `resolve_platform_control_plane_url()`. Helper execution raise ở `ENVIRONMENT in {production,staging,prod}` nếu URL = platform URL hoặc host không loopback/`.local`. Mọi call-site đọc `os.environ["COSA_CONTROL_PLANE_URL"]` chuyển sang helper phù hợp theo bảng phân loại trong spec.

**Tech Stack:** Python 3.11, pytest, FastAPI. Không migration, không TS change.

**Spec:** `docs/superpowers/specs/2026-08-28-exec-plane-split-design.md`.

## Global Constraints

- **TDD**: test đỏ → xác nhận đỏ → implement → xác nhận xanh → commit.
- **An toàn working tree** (CLAUDE.md #10): `git status` trước; partial commit (`git commit <path>`) để không gom việc song song đang staged; không `--force`/`--no-verify`.
- **Không production fallback in-memory/remote.** Test inject qua `monkeypatch.setenv`.
- **Không xoá `COSA_CONTROL_PLANE_URL`** — chỉ hạ xuống fallback cấp 2.
- Comment tiếng Việt cho why; identifier/error tiếng Anh.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `apps/cosa/config/__init__.py` | (tạo nếu chưa có) package marker |
| `apps/cosa/config/planes.py` | `resolve_execution_plane_url()`, `resolve_platform_control_plane_url()` + fail-fast |
| `apps/cosa/composition/agent_plane.py` | `run_scheduler`/`run_lease_client` → execution; `connector_grant_client` → platform; event-intake block → gọi helper |
| `apps/cosa/worker/handlers.py` | run-dispatch (:349,412) → execution |
| `apps/cosa/api/routes.py` | `/connectors/*` → platform; `/schedules*` → execution; ingestion-control → platform |
| `apps/cosa/knowledge_ingestion/control_plane_client.py` | → platform |
| `apps/cosa/capabilities/connector_grant_client.py` | → platform |
| `apps/cosa/policies/company_policy_client.py` | → platform |
| `.env.example`, `Makefile` | 2 biến mới; legacy đánh dấu deprecated |
| `tests/apps/cosa/test_exec_plane_split.py` | helper behaviour + boundary + grep guard |

---

### Task 1: Plane-resolution helper

**Files:**
- Create: `apps/cosa/config/__init__.py` (nếu chưa có), `apps/cosa/config/planes.py`
- Test: `tests/apps/cosa/test_exec_plane_split.py`

**Interfaces:**
- Produces: `resolve_execution_plane_url() -> str`, `resolve_platform_control_plane_url() -> str` (module `apps.cosa.config.planes`).

- [ ] **Step 1: Viết test đỏ**

Create `tests/apps/cosa/test_exec_plane_split.py`:

```python
import pytest
from apps.cosa.config.planes import resolve_execution_plane_url, resolve_platform_control_plane_url


def test_defaults_to_loopback(monkeypatch):
    for v in ("COSA_EXECUTION_PLANE_URL", "COSA_PLATFORM_CONTROL_PLANE_URL", "COSA_CONTROL_PLANE_URL", "ENVIRONMENT", "APP_ENV"):
        monkeypatch.delenv(v, raising=False)
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"
    assert resolve_platform_control_plane_url() == "http://127.0.0.1:4001"


def test_legacy_var_is_fallback_for_both(monkeypatch):
    for v in ("COSA_EXECUTION_PLANE_URL", "COSA_PLATFORM_CONTROL_PLANE_URL", "ENVIRONMENT", "APP_ENV"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("COSA_CONTROL_PLANE_URL", "http://legacy:9000")
    assert resolve_execution_plane_url() == "http://legacy:9000"
    assert resolve_platform_control_plane_url() == "http://legacy:9000"


def test_new_vars_win_over_legacy(monkeypatch):
    monkeypatch.setenv("COSA_CONTROL_PLANE_URL", "http://legacy:9000")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:4001")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "http://platform:4001")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"
    assert resolve_platform_control_plane_url() == "http://platform:4001"


def test_production_rejects_execution_equal_to_platform(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://platform.example.com")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example.com")
    with pytest.raises(RuntimeError, match="must not equal the platform"):
        resolve_execution_plane_url()


def test_production_rejects_remote_execution_host(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://remote.example.com")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example.com")
    with pytest.raises(RuntimeError, match="must be local"):
        resolve_execution_plane_url()


def test_production_allows_loopback_and_dot_local(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example.com")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:4001")
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://node1.local:4001")
    assert resolve_execution_plane_url() == "http://node1.local:4001"


def test_no_direct_legacy_env_reads_outside_helper():
    import subprocess, pathlib
    repo = pathlib.Path(__file__).resolve().parents[3]
    out = subprocess.run(
        ["grep", "-rn", "COSA_CONTROL_PLANE_URL", str(repo / "apps/cosa"), "--include=*.py"],
        capture_output=True, text=True,
    ).stdout
    offenders = [l for l in out.splitlines()
                 if "config/planes.py" not in l and "/test" not in l and "_test" not in l]
    assert not offenders, "direct COSA_CONTROL_PLANE_URL reads remain:\n" + "\n".join(offenders)
```

- [ ] **Step 2: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_exec_plane_split.py -q`
Expected: FAIL — `apps.cosa.config.planes` chưa tồn tại; `test_no_direct_legacy_env_reads_outside_helper` cũng FAIL (còn nhiều call-site).

- [ ] **Step 3: Viết `planes.py`**

Create `apps/cosa/config/__init__.py` (rỗng nếu chưa có). Create `apps/cosa/config/planes.py` — copy nguyên khối từ spec §Decision.1.

- [ ] **Step 4: Chạy — helper tests xanh (grep guard vẫn đỏ)**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_exec_plane_split.py -q -k "not no_direct_legacy"`
Expected: PASS (6 passed). `test_no_direct_legacy_env_reads_outside_helper` vẫn FAIL — Task 2 xử.

- [ ] **Step 5: Commit**

```bash
git status
git add apps/cosa/config/__init__.py apps/cosa/config/planes.py tests/apps/cosa/test_exec_plane_split.py
git commit apps/cosa/config/__init__.py apps/cosa/config/planes.py tests/apps/cosa/test_exec_plane_split.py \
  -m "feat(config): execution vs platform plane URL resolution with fail-fast"
```

---

### Task 2: Repoint every call-site + config docs

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py`, `apps/cosa/worker/handlers.py`, `apps/cosa/api/routes.py`, `apps/cosa/knowledge_ingestion/control_plane_client.py`, `apps/cosa/capabilities/connector_grant_client.py`, `apps/cosa/policies/company_policy_client.py`
- Modify: `.env.example`, `Makefile`

**Interfaces:**
- Consumes: `resolve_execution_plane_url`, `resolve_platform_control_plane_url` (Task 1).
- Produces: 0 direct `os.environ[...COSA_CONTROL_PLANE_URL...]` reads ngoài helper.

- [ ] **Step 1: Repoint theo bảng phân loại (spec §Decision.2)**

- `agent_plane.py`:
  - `:206-218` event-intake block → `execution_url = resolve_execution_plane_url()`, `platform_url = resolve_platform_control_plane_url()`, xoá inline fail-fast (helper lo). Giữ mọi dùng `execution_url`/`platform_url` phía dưới.
  - `:320-322` → `control_plane_url` đổi tên thành `execution_plane_url = resolve_execution_plane_url()`; `run_scheduler`/`run_lease_client` dùng nó.
  - `:366` → `connector_grant_client = ConnectorGrantHttpClient(base_url=resolve_platform_control_plane_url())`.
  - Thêm `from apps.cosa.config.planes import resolve_execution_plane_url, resolve_platform_control_plane_url`.
- `worker/handlers.py:349,412` → `resolve_execution_plane_url()` + import.
- `routes.py`:
  - `:733,755,779,804` (`/connectors/*`) → `resolve_platform_control_plane_url()`.
  - `:828,870,908` (`/schedules*`) → `resolve_execution_plane_url()`.
  - `:954,1044,1120` (ingestion control) → `resolve_platform_control_plane_url()`.
  - Thêm import 1 lần ở đầu file.
- `knowledge_ingestion/control_plane_client.py:39` → `resolve_platform_control_plane_url()` (giữ tham số `control_plane_url` override; chỉ đổi default).
- `capabilities/connector_grant_client.py:20` → `resolve_platform_control_plane_url()` (giữ `base_url or ...`).
- `policies/company_policy_client.py:38` → `resolve_platform_control_plane_url()` (giữ `base_url or ...`).

- [ ] **Step 2: Config docs**

- `.env.example:42`: đổi thành 3 dòng —
  ```
  # DEPRECATED fallback — set the two below instead
  COSA_CONTROL_PLANE_URL=http://127.0.0.1:4001
  COSA_EXECUTION_PLANE_URL=http://127.0.0.1:4001
  COSA_PLATFORM_CONTROL_PLANE_URL=http://127.0.0.1:4001
  ```
- `Makefile:36` comment: nêu `COSA_EXECUTION_PLANE_URL` (local scheduler/lease) + `COSA_PLATFORM_CONTROL_PLANE_URL` (VPS identity/connector/policy).

- [ ] **Step 3: Chạy — grep guard + full apps/cosa suite**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_exec_plane_split.py -q`
Expected: PASS (7 passed, gồm `test_no_direct_legacy_env_reads_outside_helper`).

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa -q`
Expected: PASS — không regression. Sửa test nào hard-code `COSA_CONTROL_PLANE_URL` assumption nếu vỡ (dùng helper mới hoặc setenv cả 2 var).

- [ ] **Step 4: Manual boundary check**

```bash
ENVIRONMENT=production COSA_EXECUTION_PLANE_URL=https://x.example.com COSA_PLATFORM_CONTROL_PLANE_URL=https://x.example.com \
  PYTHONPATH=. .venv/bin/python -c "from apps.cosa.composition.agent_plane import build_cosa_agent_plane; build_cosa_agent_plane()" 2>&1 | grep -q "must not equal the platform" && echo OK
```

- [ ] **Step 5: Commit**

```bash
git status
git add apps/cosa/composition/agent_plane.py apps/cosa/worker/handlers.py apps/cosa/api/routes.py \
        apps/cosa/knowledge_ingestion/control_plane_client.py apps/cosa/capabilities/connector_grant_client.py \
        apps/cosa/policies/company_policy_client.py .env.example Makefile
git commit apps/cosa/composition/agent_plane.py apps/cosa/worker/handlers.py apps/cosa/api/routes.py \
  apps/cosa/knowledge_ingestion/control_plane_client.py apps/cosa/capabilities/connector_grant_client.py \
  apps/cosa/policies/company_policy_client.py .env.example Makefile \
  -m "refactor(config): repoint call-sites to execution/platform plane URLs"
```

---

## Self-Review

| Spec DoD | Task |
| --- | --- |
| 1. helper raise ở prod khi execution==platform / host không local; ok ở dev/test | Task 1 Steps 1,3 |
| 2. run dispatch/lease/schedule → execution; connector/policy/ingestion → platform | Task 2 Step 1 (bảng phân loại) |
| 3. 0 direct legacy env reads ngoài helper | Task 2 Step 1 + `test_no_direct_legacy_env_reads_outside_helper` |
| 4. `.env.example` + `Makefile` có 2 var mới; legacy deprecated | Task 2 Step 2 |
| 5. test hiện có xanh + test helper mới | Task 2 Step 3 |

**Placeholder scan:** helper code copy nguyên từ spec; test có assertion thật; call-site list là line-number cụ thể từ grep 2026-08-28 (verify lại lúc chạy — tree đang churn).
**Type consistency:** `resolve_execution_plane_url` / `resolve_platform_control_plane_url` — hai tên dùng verbatim ở Task 2 và mọi test.

---

## Verification (end-to-end)

```
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa -q
grep -rn 'COSA_CONTROL_PLANE_URL' apps/cosa --include='*.py' | grep -v 'config/planes.py' | grep -v test   # → 0
```

## Execution Handoff

Sau plan này → P1 Task 2 (durable supervisor) hết bị chặn. Không cho phép deploy VPS, cài broker, xoá dữ liệu.
