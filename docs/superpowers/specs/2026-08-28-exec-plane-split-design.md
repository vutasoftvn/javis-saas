# Spec: SPEC-EXEC-PLANE-SPLIT — tách execution plane khỏi platform control plane

- Parent spec: `docs/superpowers/specs/2026-08-28-event-driven-agent-operating-model-design.md` (commit `cb080b77`) — mục "Phụ thuộc ngoài".
- Là **P0 prerequisite** đã tách riêng: gỡ chặn P1 Task 2 (durable multi-agent supervisor) và củng cố ranh giới local-first cho toàn bộ đường dispatch/lease.

---

## Context — vì sao

`apps/cosa` hiện dùng **một** biến `COSA_CONTROL_PLANE_URL` cho cả hai loại concern khác bản chất:

- **Execution plane** (phải chạy tại local Workspace Runtime Node): durable run dispatch, run lease, scheduled-task, và — sắp tới — durable child task (P1 Task 2).
- **Platform control plane** (chạy tại VPS): identity/license, connector policy/entitlement, company policy, document-ingestion control record.

Xác minh trên code (2026-08-28, sau P0):

| Call-site | Hiện dùng | Phân loại đúng |
| --- | --- | --- |
| `apps/cosa/composition/agent_plane.py:206-218` | **đã có** `COSA_EXECUTION_PLANE_URL` + `COSA_PLATFORM_CONTROL_PLANE_URL` + fail-fast (execution ≠ platform, phải local ở prod) — nhưng **chỉ** cho đường event-intake | mẫu để mở rộng |
| `agent_plane.py:320-322` — `run_scheduler`, `run_lease_client` (`HttpControlPlaneSchedulerClient`, `HttpControlPlaneLeaseClient`) | `COSA_CONTROL_PLANE_URL` | **execution** ← điểm mấu chốt cho P1 Task 2 |
| `agent_plane.py:366` — `connector_grant_client` | `control_plane_url` | **platform** |
| `apps/cosa/worker/handlers.py:349,412` | `COSA_CONTROL_PLANE_URL` | **platform** (schedule-execution snapshot fetch/complete — store ở `services/cosa`) |
| `apps/cosa/api/routes.py:733,755,779,804` — `/connectors/{install,authorize,grant,revoke}` | `COSA_CONTROL_PLANE_URL` | **platform** |
| `apps/cosa/api/routes.py:828,870,908` — `/schedules{,/list,/run-now}` | `COSA_CONTROL_PLANE_URL` | **platform** (schedule store + CRUD ở `services/cosa` control plane; chỉ `run_scheduler`/`run_lease_client` là execution) |
| `apps/cosa/api/routes.py:954,1044,1120` — document ingestion control record (`cosa_document_ingestion_client`) | `COSA_CONTROL_PLANE_URL` | **platform** (giữ nguyên; đưa ingestion về local là scope khác) |
| `apps/cosa/knowledge_ingestion/control_plane_client.py:39` | `COSA_CONTROL_PLANE_URL` | **platform** |
| `apps/cosa/capabilities/connector_grant_client.py:20` | `COSA_CONTROL_PLANE_URL` | **platform** |
| `apps/cosa/policies/company_policy_client.py:38` | `COSA_CONTROL_PLANE_URL` | **platform** |
| `.env.example:42`, `Makefile:36` | chỉ `COSA_CONTROL_PLANE_URL` | thêm 2 biến mới |

**Rủi ro nếu không tách:** một Workspace Runtime Node cấu hình `COSA_CONTROL_PLANE_URL` trỏ VPS sẽ **âm thầm** queue business work (run, child task, lease) lên platform từ xa — vi phạm `ADR-LOCAL-FIRST-001 §Execution-plane rule`.

**Kết quả mong muốn:** hai biến tách bạch với ngữ nghĩa rõ; một helper dùng chung có fail-fast; mọi call-site trỏ đúng plane; `COSA_CONTROL_PLANE_URL` còn lại **chỉ** làm fallback deprecated trong giai đoạn chuyển tiếp.

### Phân loại `/schedules` endpoints (đã chốt khi triển khai)

`workspaceScheduleDefinitions`/`workspaceScheduleExecutions` (`services/cosa/storage/control-plane-schema.ts`) sống ở `services/cosa` control plane. CRUD/snapshot-fetch của schedule là **platform** — chỉ `run_scheduler`/`run_lease_client` (durable run dispatch/lease trong `agent_plane.py`) là **execution**. Đây là ranh giới đơn giản + an toàn: hậu quả sai về "platform" chỉ là metadata management proxy qua VPS; không có business-work-queuing nào lọt ra platform. Nếu về sau schedule store tách khỏi `services/cosa`, xét lại — không chặn spec này. Code đã landed theo phân loại này (`ed05250c`).

---

## Decision — thiết kế

### 1. Module config dùng chung: `apps/cosa/config/planes.py`

```python
from __future__ import annotations
import os
from urllib.parse import urlparse

_LEGACY_VAR = "COSA_CONTROL_PLANE_URL"
_DEFAULT = "http://127.0.0.1:4001"
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_PROD_ENVS = {"production", "staging", "prod"}


def _env_name() -> str:
    return os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()


def resolve_platform_control_plane_url() -> str:
    """VPS platform: identity/license, connector policy, company policy,
    document-ingestion control record."""
    return os.environ.get(
        "COSA_PLATFORM_CONTROL_PLANE_URL",
        os.environ.get(_LEGACY_VAR, _DEFAULT),
    ).rstrip("/")


def resolve_execution_plane_url() -> str:
    """Local Workspace Runtime Node: run dispatch, lease, scheduled task,
    durable child task. Fail-fast ở production nếu bị trỏ ra platform từ xa."""
    url = os.environ.get(
        "COSA_EXECUTION_PLANE_URL",
        os.environ.get(_LEGACY_VAR, _DEFAULT),
    ).rstrip("/")
    if _env_name() in _PROD_ENVS:
        platform = resolve_platform_control_plane_url()
        if url == platform:
            raise RuntimeError(
                "COSA_EXECUTION_PLANE_URL must not equal the platform control-plane URL "
                "(ADR-LOCAL-FIRST-001 §Execution-plane rule) — set it to the local node"
            )
        host = urlparse(url).hostname or ""
        if host not in _LOCAL_HOSTS and not host.endswith(".local"):
            raise RuntimeError(
                f"COSA_EXECUTION_PLANE_URL must be local for a Workspace Runtime Node, got host={host!r}"
            )
    return url
```

- `agent_plane.py:206-218` (đường event-intake) refactor để gọi helper này thay vì inline — hành vi giữ nguyên.
- Không có production in-memory / remote fallback. Test inject qua `monkeypatch.setenv`.

### 2. Repoint call-sites

| Call-site | Đổi thành |
| --- | --- |
| `agent_plane.py` — `run_scheduler`, `run_lease_client` (:320-322) | `resolve_execution_plane_url()` |
| `agent_plane.py` — `connector_grant_client` (:366) | `resolve_platform_control_plane_url()` |
| `agent_plane.py` — event-intake block (:206-218) | gọi helper (giữ hành vi) |
| `worker/handlers.py:349,412` | `resolve_platform_control_plane_url()` |
| `routes.py` — `/connectors/*` (:733,755,779,804) | `resolve_platform_control_plane_url()` |
| `routes.py` — `/schedules*` (:828,870,908) | `resolve_platform_control_plane_url()` |
| `routes.py` — document ingestion (:954,1044,1120) | `resolve_platform_control_plane_url()` |
| `knowledge_ingestion/control_plane_client.py:39` | `resolve_platform_control_plane_url()` |
| `capabilities/connector_grant_client.py:20` | `resolve_platform_control_plane_url()` |
| `policies/company_policy_client.py:38` | `resolve_platform_control_plane_url()` |

### 3. Config docs

- `.env.example`: giữ `COSA_CONTROL_PLANE_URL` (đánh dấu `# DEPRECATED — fallback; set the two below instead`), thêm:
  ```
  COSA_EXECUTION_PLANE_URL=http://127.0.0.1:4001   # local Workspace Runtime Node scheduler/lease
  COSA_PLATFORM_CONTROL_PLANE_URL=http://127.0.0.1:4001   # VPS identity/license/connector/policy
  ```
- `Makefile:36` comment: cập nhật nêu 2 biến mới.

### 4. Deprecation

`COSA_CONTROL_PLANE_URL` **không xoá** trong spec này (giảm blast radius). Chỉ còn là fallback cấp 2. Một test cảnh báo (không fail) nếu chỉ có legacy var mà thiếu cả hai var mới ở non-prod; **fail** nếu thiếu ở prod đường execution (đã có trong helper).

---

## Không thuộc phạm vi

- Đưa document-ingestion control record về local node (giữ platform).
- Xoá `COSA_CONTROL_PLANE_URL`.
- Đổi `services/cosa` (control-plane-scheduler vẫn là cơ chế; deployment profile local là cấu hình vận hành, không phải code change ở đây).
- P1 Task 2 (durable supervisor) — spec riêng, chỉ *phụ thuộc* spec này.

---

## Definition of done

1. `resolve_execution_plane_url()` raise ở `ENVIRONMENT=production` khi URL = platform URL hoặc host không local; trả URL bình thường ở development/test.
2. `run_scheduler`/`run_lease_client` dùng execution plane URL; connector/policy/ingestion-control/schedule-CRUD/worker-schedule-snapshot dùng platform URL.
3. Không call-site nào trong `apps/cosa` (ngoài `config/planes.py` và test) đọc trực tiếp `os.environ["COSA_CONTROL_PLANE_URL"]`.
4. `.env.example` + `Makefile` có 2 biến mới; legacy var đánh dấu deprecated.
5. Toàn bộ test hiện có của `apps/cosa` vẫn xanh; thêm test cho helper + boundary.

---

## Verification

```
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa -q
grep -rn 'COSA_CONTROL_PLANE_URL' apps/cosa --include='*.py' | grep -v 'config/planes.py' | grep -v test   # → 0
```
Manual: set `ENVIRONMENT=production COSA_EXECUTION_PLANE_URL=https://platform.example.com` → `build_cosa_agent_plane()` raise. Set về loopback → OK.

---

## Execution handoff

Sau khi duyệt → plan chi tiết task-by-task → thực thi. Không cho phép deploy VPS, cài broker, xoá dữ liệu.
