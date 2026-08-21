# Central Control Plane: Hợp nhất Schema qua Alembic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hợp nhất 2 schema Postgres đang lệch nhau của COSA Central Control Plane (`infra/supabase/migrations/001_initial_central_control_plane.sql` và `deploy/central_vps/init_central_postgres.sql`) thành 1 nguồn sự thật duy nhất quản lý bằng Alembic, chốt PK trung tâm là BigInt Snowflake (theo Quyết định 5 đã chốt), và chuyển cả 2 nơi hiện đang áp dụng schema bằng SQL tay sang chạy migration.

**Architecture:** Tạo 1 lịch sử Alembic độc lập cho Central Control Plane — `backend/alembic_control_plane/` + `backend/alembic_control_plane.ini` — tách biệt hoàn toàn khỏi `backend/alembic/` (Local Business DB), theo đúng khuyến nghị của Quyết định 2. Model ORM nằm ở `backend/app/platform/control_plane/` với `ControlPlaneBase` (metadata riêng, KHÔNG dùng chung `app.db.base_class.Base`). Toàn bộ bảng control-plane nằm trong schema Postgres `control_plane` (không phải `public`) — quyết định bổ sung có bằng chứng cụ thể (xem "Phát hiện quan trọng" bên dưới) để tránh trùng tên bảng với Local Business DB khi 2 DB tạm thời co-locate cùng 1 Postgres instance (cấu hình mặc định hiện tại trên Hostinger). `infra/supabase/migrations/001_initial_central_control_plane.sql` (biến thể BigInt Snowflake) trở thành nguồn nội dung cho baseline migration; `deploy/central_vps/init_central_postgres.sql` (biến thể UUID) bị loại bỏ về mặt PK. Cả 2 file SQL gốc được đánh dấu superseded bằng header comment, không xoá.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (Declarative + `Mapped`/`mapped_column`), Alembic ≥1.13.0, PostgreSQL 16, pytest, Docker Compose.

**Spec:** `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md` — Quyết định 2 (dòng 176-197, đã chốt, không re-litigate); tham chiếu Quyết định 5 (dòng 285-308) cho chính sách "thuần Snowflake ID, không UUID"; tham chiếu Quyết định 6.2 (dòng 332-338) cho convention "đánh dấu superseded, không xoá file".

## Global Constraints

- Mọi migration phải reversible khi khả thi (`downgrade()` đầy đủ) và mọi thay đổi schema phải đi qua Alembic migration — không hand-edit schema đang chạy (CLAUDE.md §16).
- PK trung tâm chốt là **BigInt Snowflake** (`generate_snowflake_id()` từ `app.core.snowflake`, qua `SnowflakeIDMixin` có sẵn ở `app.db.snowflake_model`) — không giới thiệu UUID dưới bất kỳ hình thức nào (Quyết định 5, đã chốt).
- Không xoá `infra/supabase/migrations/001_initial_central_control_plane.sql` hay `deploy/central_vps/init_central_postgres.sql` — chỉ đánh dấu superseded bằng header comment trỏ tới Alembic history mới, đúng convention retire đã có ở Quyết định 6.2.
- **Không đổi**: schema/model của `PlatformOutbox`/`PlatformInbox`/`LocalEntitlementSnapshot` (`backend/app/platform/sync/models.py`), cơ chế HMAC/signature của `EntitlementManager` (`backend/app/platform/sync/entitlement_manager.py`, `entitlement_crypto.py`), cơ chế outbox/backoff/idempotent-ACK của `PlatformSyncWorker` (`backend/app/platform/sync/sync_worker.py`, `outbox_service.py`). Đã verify: các bảng này (`platform_outbox`, `platform_inbox`, `local_entitlement_snapshots`) không trùng tên và không xuất hiện trong 2 file SQL control-plane — migration của plan này không đụng tới.
- Không thiết kế/triển khai bất kỳ thứ gì liên quan InsForge — đã chốt ngoài phạm vi (Quyết định 2).
- Không đụng vào phần `APP_ROLE`/`create_app(role)`/`central_main.py`/`full_main.py`/lệnh chạy của `central_api` — đó là phạm vi Quyết định 3 (self-host app factory), đang được 1 plan khác thực hiện song song. Plan này chỉ sửa **cơ chế áp dụng schema** (service `migrate-control-plane`/init script), không sửa cách `central_api` khởi động.
- Không đụng vào ADK orchestrator (Quyết định 1) hay hợp nhất định danh Agent/WorkforceMember (Quyết định 4) — 2 plan khác, độc lập.
- Tái dùng `SnowflakeIDMixin`/`generate_snowflake_id()` có sẵn (`app.db.snowflake_model`, `app.core.snowflake`) — không viết lại bộ sinh ID mới cho control-plane (CLAUDE.md §14 — No Duplicate Architecture).
- `make boundary-check` cấm `uuid\.|uuid\.UUID|PG_UUID|postgresql\.UUID|sa\.UUID` trong `backend/app` — model/migration mới không được dùng bất kỳ kiểu UUID nào.

## Ghi chú thiết kế quan trọng (đọc trước khi thực thi)

### 3 vai trò DB không được lẫn lộn (yêu cầu tường minh từ Quyết định 2)
1. **Personal Business DB** (desktop/self-host founder) — business truth ở Personal Mode.
2. **Team Business DB** (cloud/VPS) — business truth khi workspace promote thành Team (Quyết định 3, không thuộc phạm vi plan này).
3. **COSA Central Control Plane** (account/license/entitlement/device/update) — **đối tượng của plan này**.

DB #2 và #3 không nhất thiết là cùng 1 DB. Trên thực tế, cấu hình mặc định hiện tại (`docker-compose.yml` gốc, biến `CONTROL_PLANE_DATABASE_URL` mặc định trỏ vào cùng service `postgres`/database `javis` với Local Business DB — xem `.env.example` dòng 11) **đang co-locate #1 và #3 vào cùng 1 database**. Plan này không đổi topology đó (thuộc phạm vi hạ tầng/Quyết định 3), nhưng bổ sung 1 lớp cách ly ở mức schema Postgres (xem mục kế) để giảm rủi ro cụ thể đã phát hiện được khi co-locate.

### Phát hiện quan trọng phát sinh trong lúc research (KHÔNG có trong đề xuất gốc — cần biết trước khi thực thi)

1. **Va chạm tên bảng thật giữa Local Business DB và Central Control Plane**: `backend/app/platform/core/deployment_models.py:14` định nghĩa `class Deployment(Base): __tablename__ = "deployments"` — model này thuộc Local Business DB (`app.db.base.Base`, quản lý bởi `backend/alembic/`), sống ở schema `public`. Cả 2 file SQL control-plane cũng có bảng `public.deployments` (VPS deployment registry, cột hoàn toàn khác). Nếu áp schema control-plane vào **cùng database** với Local Business DB (đúng là cấu hình mặc định hiện tại trên Hostinger, xem trên) mà không cách ly, `CREATE TABLE public.deployments` của control-plane sẽ đụng thẳng bảng `deployments` của Local Business DB — 1 trong 2 sẽ bị bỏ qua (`IF NOT EXISTS`) hoặc lỗi tạo trùng bảng. Đây là lý do cụ thể, đã verify, khiến plan này đưa toàn bộ bảng control-plane vào schema Postgres riêng **`control_plane`** thay vì `public` — không phải suy đoán, mà là sửa 1 lỗi thật đang tiềm ẩn trong cấu hình mặc định.
2. **`platform_users` lệch nhau nhiều hơn kiểu PK**: `infra/supabase/migrations/...` dùng cột `hashed_password TEXT`, cho phép `email`/`phone` cùng nullable (ràng buộc `CHECK (email IS NOT NULL OR phone IS NOT NULL)`), có `last_login_at`, và index `email`/`phone` là partial index (`WHERE ... IS NOT NULL`) cộng thêm index `status`. `deploy/central_vps/init_central_postgres.sql` dùng tên cột khác — `password_hash VARCHAR(255)` — bắt buộc `email NOT NULL`, không có `last_login_at`, không có index `phone`/`status`. Theo quyết định "file nào thắng PK thì thắng toàn bộ" (infra/supabase, vì PK BigInt), baseline mới port nguyên bản `hashed_password`/nullable email-or-phone/`last_login_at`/partial index — bỏ hẳn biến thể `password_hash`/email-NOT-NULL của `central_vps`.
3. **Bảng `user_sessions` (session/refresh-token management) chỉ tồn tại ở `infra/supabase/migrations/...`, hoàn toàn vắng mặt ở `deploy/central_vps/init_central_postgres.sql`** — dù cả 2 file đều tự nhận "Custom JWT Auth". Đây là 1 bảng bị rơi mất khi 2 file drift, không phải cố ý loại bỏ. Baseline mới giữ lại bảng này.
4. **Bằng chứng khả năng đã deploy thật lên production — CẦN CẢNH BÁO, không giả định chỉ là dev**: `deploy/central_vps/README.md` mô tả quy trình triển khai qua Coolify với domain thật `api.vutasoft.com`, repo GitHub thật `vutasoftvn/javis-saas`, và 1 connection string nội bộ trông như secret thật do Coolify tự sinh (`postgres://postgres:tAb68Nrs0nhBwyBWinSaP2ZlMtsj2xGklfnkxNGHdyp6fpItPGMNZJI8QTSo6S5A@l51e7yw5swvyz3eesd4v5w9j:5432/postgres`) — không phải placeholder kiểu `<PASSWORD>`. README hướng dẫn "Khởi tạo dữ liệu (Init Script): copy toàn bộ nội dung `init_central_postgres.sql` ... execute" — tức là bảng `platform_users`/`companies`/`licenses`... ở đó (nếu đã thực sự chạy) đang dùng **PK kiểu UUID**. Repo không cho cách xác nhận chắc chắn 100% việc này đã thực sự chạy với dữ liệu thật hay chỉ là tài liệu chưa dùng tới — vì vậy: **task cuối của plan này (đánh dấu superseded) phải ghi cảnh báo này thẳng vào file `init_central_postgres.sql`**, và plan này **không** tự động trỏ bất kỳ deployment thật nào vào Alembic history mới — đó là quyết định vận hành cần founder xác nhận riêng trước khi chạy `alembic upgrade head` nhắm vào 1 database đã có dữ liệu.
5. **`backend/app/platform/sync/entitlement_crypto.py` và `outbox_service.py` gọi `uuid.UUID(company_id)`/`uuid.UUID(event_id)` thật trên dữ liệu định danh trung tâm** (`entitlement_crypto.py:82,106,136,213,236,312,328`; `outbox_service.py:48-50,92-93,135-136,173-174`) — tức là code đồng bộ ĐANG chạy giả định `company_id`/`project_id` phía Central là chuỗi UUID hợp lệ (khớp biến thể `deploy/central_vps/init_central_postgres.sql`), không phải BigInt Snowflake. Đây là hệ quả thật của quyết định "PK trung tâm = BigInt" (Quyết định 5) chưa được truy hết trong đề xuất gốc: nếu 1 `company_id`/`project_id` Snowflake (chuỗi số, không đúng định dạng UUID) đi qua `uuid.UUID(...)`, code sẽ ném `ValueError`. Theo đúng yêu cầu "Không đổi ... cơ chế HMAC/signature của `EntitlementManager` ... cơ chế outbox ... của `PlatformSyncWorker`", **plan này KHÔNG sửa 2 file này** — chỉ ghi nhận đây là rủi ro/nợ kỹ thuật có thật, cần 1 task riêng (ngoài phạm vi plan này) trước khi có bất kỳ tích hợp thật nào giữa client và 1 Central instance đã chạy Alembic schema mới.
6. **Quan sát phụ, không thuộc phạm vi xử lý**: `make boundary-check` cấm mọi `uuid\.` trong `backend/app`, nhưng `rg -n 'uuid\.' backend/app --glob '*.py'` hiện trả về nhiều kết quả thật (bao gồm cả 2 file ở mục 5, và nhiều chỗ dùng `uuid.uuid4()` để sinh correlation/event id — không phải PK). Nhiều khả năng target `boundaries` trong CI hiện đang đỏ hoặc quy tắc này chưa từng được biết là quá rộng. Không thuộc phạm vi Quyết định 2 — chỉ ghi nhận để không hiểu lầm rằng model mới của plan này là nguyên nhân nếu `boundary-check` fail.
7. **Quyết định thiết kế: KHÔNG port hàm SQL `generate_snowflake_id()`/sequence `snowflake_id_seq` mà cả 2 file gốc đều định nghĩa** (`infra/supabase/migrations/...:16-34` và tương tự — dùng làm `DEFAULT` cấp cột cho insert bằng SQL thô). Baseline Alembic mới chỉ dùng `SnowflakeIDMixin`/`generate_snowflake_id()` **phía Python** (`app.core.snowflake`, qua ORM, giống hệt cách 61 file model hiện có của Local Business DB đang làm — đã verify baseline migration `9a470e50097b_snowflake_runtime_baseline.py` của Local Business DB **cũng không** tạo hàm/sequence phía Postgres, chỉ dựa vào default phía Python). Đây là lựa chọn có chủ đích để nhất quán với convention thật của dự án (CLAUDE.md §14 — không tạo 2 cách sinh ID song song), không phải bỏ sót. Hệ quả: mọi INSERT vào bảng control-plane phải đi qua ORM (hoặc tự cung cấp `id` tường minh) — không có cột `DEFAULT` cấp Postgres cho `id` như 2 file SQL gốc.

## Tổng quan file

| File | Vai trò |
|---|---|
| `backend/app/platform/control_plane/__init__.py` | Package mới |
| `backend/app/platform/control_plane/db.py` | `ControlPlaneBase` (metadata riêng, schema `control_plane`) |
| `backend/app/platform/control_plane/models.py` | Toàn bộ ORM model của Central Control Plane |
| `backend/alembic_control_plane.ini` | Alembic config riêng cho control-plane |
| `backend/alembic_control_plane/env.py` | Alembic env — đọc `CONTROL_PLANE_DATABASE_URL`/`DATABASE_URL`, tự tạo schema `control_plane` trước khi track version |
| `backend/alembic_control_plane/script.py.mako` | Template revision (copy nguyên bản từ `backend/alembic/script.py.mako`) |
| `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py` | Baseline migration — toàn bộ schema hợp nhất |
| `backend/app/tests/test_control_plane_migration_metadata.py` | Test metadata thuần Python (theo mẫu `test_migration_metadata.py` có sẵn) |
| `backend/app/tests/migrations/test_control_plane_baseline_migration.py` | Test round-trip thật trên Postgres (`RUN_DB_INTEGRATION=1`) |
| `backend/Dockerfile.api` | Thêm COPY `alembic_control_plane/` + ini |
| `docker-compose.yml` (root) | Service `migrate-control-plane` chuyển từ raw `psql` sang Alembic |
| `deploy/central_vps/docker-compose.yaml` | Bỏ init SQL mount, thêm service `migrate_control_plane` chạy Alembic |
| `Makefile` | Thêm bước alembic control-plane vào `backend-integration-test`/`migration-check` |
| `.github/workflows/quality.yml` | Thêm bước `alembic -c backend/alembic_control_plane.ini upgrade head`/`check` vào job `backend` |
| `infra/supabase/migrations/001_initial_central_control_plane.sql` | Đánh dấu superseded (header comment, không xoá) |
| `deploy/central_vps/init_central_postgres.sql` | Đánh dấu superseded + cảnh báo dữ liệu thật (header comment, không xoá) |

---

### Task 1: `ControlPlaneBase` — metadata riêng, cách ly khỏi Local Business DB

**Files:**
- Create: `backend/app/platform/control_plane/__init__.py`
- Create: `backend/app/platform/control_plane/db.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py`

**Interfaces:**
- Produces: `CONTROL_PLANE_SCHEMA: str = "control_plane"`, `class ControlPlaneBase(DeclarativeBase)` với `ControlPlaneBase.metadata.schema == "control_plane"` — mọi model ở Task 4-9 kế thừa class này.

- [ ] **Step 1: Viết test thất bại**

```python
# backend/app/tests/test_control_plane_migration_metadata.py
"""Regression tests cho schema Alembic riêng của COSA Central Control Plane
(Quyết định 2, docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md)."""

import os
import subprocess
import sys
from pathlib import Path


def _run(code: str) -> subprocess.CompletedProcess:
    backend_root = Path(__file__).resolve().parents[2]
    environment = {**os.environ, "PYTHONPATH": str(backend_root)}
    return subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )


def test_control_plane_base_is_isolated_from_local_business_metadata():
    code = """
from app.platform.control_plane.db import ControlPlaneBase, CONTROL_PLANE_SCHEMA
from app.db.base_class import Base as LocalBase

assert CONTROL_PLANE_SCHEMA == "control_plane"
assert ControlPlaneBase.metadata.schema == "control_plane"
assert ControlPlaneBase.metadata is not LocalBase.metadata
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.platform.control_plane'`

- [ ] **Step 3: Viết implementation tối thiểu**

```python
# backend/app/platform/control_plane/__init__.py
```
(file rỗng — đánh dấu package)

```python
# backend/app/platform/control_plane/db.py
"""Declarative base riêng cho COSA Central Control Plane (Quyết định 2,
docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md dòng 176-197).

KHÔNG dùng chung `app.db.base_class.Base`/`app.db.base.Base` của Local
Business DB. Central Control Plane là 1 trong 3 vai trò DB tách biệt
(Personal Business DB / Team Business DB / Central Control Plane) — xem
Quyết định 2. Khi tạm thời co-locate cùng 1 Postgres instance với Local
Business DB (cấu hình mặc định hiện tại của `docker-compose.yml` gốc, biến
`CONTROL_PLANE_DATABASE_URL`), mọi bảng nằm trong schema Postgres
`control_plane` — KHÔNG phải `public` — để tránh trùng tên bảng với Local
Business DB. Va chạm cụ thể đã verify: `app.platform.core.deployment_models
.Deployment.__tablename__ == "deployments"` (Local, schema `public`) trùng
tên với bảng control-plane `deployments` (VPS deployment registry, cột hoàn
toàn khác) nếu cả 2 cùng nằm `public` trong cùng 1 database.
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

CONTROL_PLANE_SCHEMA = "control_plane"


class ControlPlaneBase(DeclarativeBase):
    metadata = MetaData(schema=CONTROL_PLANE_SCHEMA)
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/__init__.py backend/app/platform/control_plane/db.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "feat(control-plane): add isolated ControlPlaneBase metadata"
```

---

### Task 2: Scaffold Alembic riêng cho Central Control Plane

**Files:**
- Create: `backend/alembic_control_plane.ini`
- Create: `backend/alembic_control_plane/env.py`
- Create: `backend/alembic_control_plane/script.py.mako`
- Create: `backend/alembic_control_plane/versions/.gitkeep`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Consumes: `ControlPlaneBase`, `CONTROL_PLANE_SCHEMA` từ Task 1.
- Produces: lệnh `alembic -c backend/alembic_control_plane.ini <cmd>` chạy được, đọc biến môi trường `CONTROL_PLANE_DATABASE_URL` (ưu tiên) rồi `DATABASE_URL` (fallback).

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `backend/app/tests/test_control_plane_migration_metadata.py`:

```python
def test_control_plane_alembic_ini_points_at_its_own_script_location():
    ini_path = Path(__file__).resolve().parents[2] / "alembic_control_plane.ini"
    assert ini_path.exists(), "backend/alembic_control_plane.ini chưa tồn tại"
    content = ini_path.read_text()
    assert "script_location = %(here)s/alembic_control_plane" in content


def test_control_plane_alembic_heads_loads_without_error():
    """`alembic heads` chỉ đọc `script_location`/thư mục `versions/` từ ini —
    KHÔNG chạy `env.py` (Alembic bỏ qua `run_env()` cho lệnh `heads`, đã verify
    thực nghiệm: `alembic heads` chạy xong dù DATABASE_URL trỏ tới cổng không
    tồn tại, trong khi `alembic upgrade --sql` cùng điều kiện thì lỗi kết nối
    thật ngay ở env.py). Vì vậy test này CHỈ xác nhận `alembic_control_plane
    .ini`/thư mục `versions/` được Alembic nhận diện đúng — KHÔNG chứng minh
    `env.py` import sạch (model chưa tồn tại ở Task này). `env.py` được verify
    đầy đủ (import ControlPlaneBase + toàn bộ model) ở Task 3 Step 4, bằng
    `alembic upgrade head --sql` (offline mode, cũng không cần Postgres thật,
    nhưng có thực sự import/thực thi env.py + migration)."""
    backend_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_control_plane.ini", "heads"],
        cwd=str(backend_root),
        env={**os.environ, "PYTHONPATH": str(backend_root)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `alembic_control_plane.ini` chưa tồn tại.

- [ ] **Step 3: Viết implementation**

```ini
# backend/alembic_control_plane.ini
# Alembic config RIÊNG cho COSA Central Control Plane (Quyết định 2).
# Tách biệt hoàn toàn khỏi backend/alembic.ini (Local Business DB) — 2 lịch
# sử migration độc lập, 2 bảng alembic_version độc lập (bảng của history này
# nằm trong schema `control_plane`, xem env.py).
[alembic]
script_location = %(here)s/alembic_control_plane
prepend_sys_path = .
path_separator = os

sqlalchemy.url = postgresql://javis:javis@localhost:5432/javis

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

```python
# backend/alembic_control_plane/env.py
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text as sa_text

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.platform.control_plane.db import ControlPlaneBase, CONTROL_PLANE_SCHEMA
import app.platform.control_plane.models  # noqa: F401  (đăng ký model vào metadata)

target_metadata = ControlPlaneBase.metadata


def _resolve_url() -> str:
    url = (
        os.environ.get("CONTROL_PLANE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=CONTROL_PLANE_SCHEMA,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # `version_table_schema` bên dưới yêu cầu schema `control_plane` đã
        # tồn tại TRƯỚC KHI Alembic tạo bảng theo dõi revision
        # (`control_plane.alembic_version`) — tạo trước ở đây, ngoài vòng đời
        # migration, để tránh lỗi "schema does not exist" ở lần chạy đầu tiên
        # trên 1 database trống.
        connection.execute(sa_text(f"CREATE SCHEMA IF NOT EXISTS {CONTROL_PLANE_SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=CONTROL_PLANE_SCHEMA,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Tạo `backend/alembic_control_plane/script.py.mako` — copy nguyên bản nội dung từ `backend/alembic/script.py.mako` (không đổi gì, chỉ là template dùng chung cho lệnh `alembic revision` sau này):

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
```

Tạo file rỗng `backend/alembic_control_plane/versions/.gitkeep` để git track thư mục trống.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS (2 test mới + test Task 1 đều xanh). `alembic heads` in ra rỗng (chưa có revision nào) nhưng exit code 0.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic_control_plane.ini backend/alembic_control_plane/env.py backend/alembic_control_plane/script.py.mako backend/alembic_control_plane/versions/.gitkeep backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "feat(control-plane): scaffold dedicated Alembic history"
```

---

### Task 3: Baseline migration — khung sườn + Section 1 (Platform Identity & Company Registry)

**Files:**
- Create: `backend/app/platform/control_plane/models.py`
- Create: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Produces: `PlatformUser`, `Company`, `CompanyMembership` ORM classes; revision `c9a1f0b2e3d4` (`down_revision=None`) với `upgrade()`/`downgrade()` chứa 3 bảng đầu.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `backend/app/tests/test_control_plane_migration_metadata.py`:

```python
def test_platform_identity_tables_use_bigint_snowflake_pk_in_control_plane_schema():
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger

tables = ControlPlaneBase.metadata.tables
for name in ("control_plane.platform_users", "control_plane.companies", "control_plane.company_memberships"):
    assert name in tables, name

pu = tables["control_plane.platform_users"]
assert isinstance(pu.c.id.type, BigInteger)
assert "hashed_password" in pu.c
assert "password_hash" not in pu.c  # ten cot da lech o deploy/central_vps, KHONG mang theo
assert pu.c.email.nullable is True
assert pu.c.phone.nullable is True
assert "last_login_at" in pu.c  # chi co o infra/supabase, central_vps thieu

company = tables["control_plane.companies"]
assert isinstance(company.c.id.type, BigInteger)
assert isinstance(company.c.created_by.type, BigInteger)

membership = tables["control_plane.company_memberships"]
assert isinstance(membership.c.company_id.type, BigInteger)
assert isinstance(membership.c.user_id.type, BigInteger)
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_control_plane_baseline_revision_has_no_down_revision():
    versions_dir = Path(__file__).resolve().parents[2] / "alembic_control_plane" / "versions"
    migration = versions_dir / "c9a1f0b2e3d4_unify_central_control_plane_schema.py"
    assert migration.exists()
    content = migration.read_text()
    assert 'revision: str = "c9a1f0b2e3d4"' in content
    assert "down_revision: Union[str, Sequence[str], None] = None" in content
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `app.platform.control_plane.models` chưa tồn tại.

- [ ] **Step 3: Viết implementation**

```python
# backend/app/platform/control_plane/models.py
"""ORM models của COSA Central Control Plane (Quyết định 2).

Nguồn: infra/supabase/migrations/001_initial_central_control_plane.sql
(bien the BigInt Snowflake — thang PK). Da bo: cot `local_project_snowflake`
va constraint `uq_company_project_local` o `projects_registry` (du thua khi
PK trung tam da la BigInt Snowflake). Da chuyen: moi bang vao schema Postgres
`control_plane` (xem db.py) thay vi `public`.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.snowflake_model import SnowflakeIDMixin
from app.platform.control_plane.db import ControlPlaneBase


class PlatformUser(SnowflakeIDMixin, ControlPlaneBase):
    """Central platform user — Custom JWT (HS256), KHONG dung Supabase Auth."""

    __tablename__ = "platform_users"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="chk_email_or_phone"),
        Index("ix_platform_users_email", "email", postgresql_where=text("email IS NOT NULL")),
        Index("ix_platform_users_phone", "phone", postgresql_where=text("phone IS NOT NULL")),
        Index("ix_platform_users_status", "status"),
    )

    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Company(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_slug", "slug"),
        Index("ix_companies_status", "status"),
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(10), default="VN")
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("platform_users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanyMembership(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "company_memberships"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
        Index("ix_company_memberships_user", "user_id"),
        Index("ix_company_memberships_company", "company_id"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    platform_role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

```python
# backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py
"""unify central control plane schema (Quyet dinh 2)

Hop nhat infra/supabase/migrations/001_initial_central_control_plane.sql
(BigInt Snowflake PK - thang) va deploy/central_vps/init_central_postgres.sql
(UUID PK - bi loai) thanh 1 nguon Alembic duy nhat. Toan bo bang nam trong
schema Postgres `control_plane` (khong phai `public`) de tranh trung ten voi
Local Business DB (vi du: bang `deployments`).

Revision ID: c9a1f0b2e3d4
Revises:
Create Date: 2026-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c9a1f0b2e3d4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTROL_PLANE_SCHEMA = "control_plane"


def upgrade() -> None:
    # An toan gap doi: env.py da CREATE SCHEMA truoc khi track version, o day
    # lap lai idempotent de migration nay tu no cung dung duoc neu chay qua
    # 1 duong khac.
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {CONTROL_PLANE_SCHEMA}")

    # ---- Section 1: Platform Identity & Company Registry ----
    op.create_table(
        "platform_users",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
        sa.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="chk_email_or_phone"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_platform_users_id", "platform_users", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index(
        "ix_platform_users_email", "platform_users", ["email"],
        unique=False, schema=CONTROL_PLANE_SCHEMA, postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "ix_platform_users_phone", "platform_users", ["phone"],
        unique=False, schema=CONTROL_PLANE_SCHEMA, postgresql_where=sa.text("phone IS NOT NULL"),
    )
    op.create_index("ix_platform_users_status", "platform_users", ["status"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "companies",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True, server_default="VN"),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.ForeignKeyConstraint(["created_by"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_companies_id", "companies", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_companies_status", "companies", ["status"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "company_memberships",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("platform_role", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "user_id", name="uq_company_user"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_company_memberships_id", "company_memberships", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_company_memberships_user", "company_memberships", ["user_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_company_memberships_company", "company_memberships", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_company_memberships_company", table_name="company_memberships", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_company_memberships_user", table_name="company_memberships", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_company_memberships_id", table_name="company_memberships", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("company_memberships", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_companies_status", table_name="companies", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_companies_slug", table_name="companies", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_companies_id", table_name="companies", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("companies", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_platform_users_status", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_platform_users_phone", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_platform_users_email", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_platform_users_id", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("platform_users", schema=CONTROL_PLANE_SCHEMA)

    op.execute(f"DROP SCHEMA IF EXISTS {CONTROL_PLANE_SCHEMA} CASCADE")
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS + verify `env.py` thực sự import sạch**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS. `alembic -c alembic_control_plane.ini heads` giờ in ra `c9a1f0b2e3d4 (head)`.

`alembic heads` (test ở Task 2) không thực thi `env.py` (đã verify thực nghiệm). Từ Task này trở đi, `models.py` đã tồn tại nên có thể verify `env.py` import sạch bằng chế độ offline (`--sql`, không cần Postgres thật — chỉ emit SQL ra stdout):

Run: `cd backend && PYTHONPATH=. CONTROL_PLANE_DATABASE_URL=postgresql://unused:unused@localhost/unused ../.venv/bin/alembic -c alembic_control_plane.ini upgrade head --sql | tail -20`
Expected: exit code 0, in ra DDL `CREATE TABLE control_plane.platform_users (...)` / `CREATE TABLE control_plane.companies (...)` / `CREATE TABLE control_plane.company_memberships (...)` — xác nhận `env.py` (Task 2) import `ControlPlaneBase`/`app.platform.control_plane.models` (Task này) không lỗi cú pháp/import, và migration's `upgrade()` không gọi `op.get_bind()` để đọc dữ liệu thật (không tương thích chế độ offline — khác với 1 migration cũ ở Local Business DB, `v13_001_flags.py`, dùng pattern đó nên KHÔNG chạy được ở chế độ offline; migration của Central Control Plane trong plan này chỉ dùng `op.create_table`/`op.create_index`/`op.execute(sa.text(...))` nên chạy offline được xuyên suốt Task 3-10).

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/models.py backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "feat(control-plane): baseline migration section 1 - platform identity"
```

---

### Task 4: Baseline migration — Section 2 (Commercial, Plans, Licenses & Entitlements)

**Files:**
- Modify: `backend/app/platform/control_plane/models.py`
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Consumes: `Company` (Task 3).
- Produces: `Plan`, `License`, `CompanyEntitlement`.

- [ ] **Step 1: Viết test thất bại**

```python
def test_commercial_tables_reference_companies_with_bigint_fk():
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger, String

tables = ControlPlaneBase.metadata.tables
plan = tables["control_plane.plans"]
assert isinstance(plan.c.id.type, String)  # business key, khong phai Snowflake

license_ = tables["control_plane.licenses"]
assert isinstance(license_.c.id.type, BigInteger)
assert isinstance(license_.c.company_id.type, BigInteger)

entitlement = tables["control_plane.company_entitlements"]
assert isinstance(entitlement.c.company_id.type, BigInteger)
assert entitlement.c.company_id.primary_key is True
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `control_plane.plans` chưa tồn tại trong metadata.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `backend/app/platform/control_plane/models.py`:

```python
class Plan(ControlPlaneBase):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_limits: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1},
    )
    default_features: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {"marketing": True, "crm": True, "finance": False, "custom_domain": False},
    )
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class License(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "licenses"
    __table_args__ = (
        Index("ix_licenses_company", "company_id"),
        Index("ix_licenses_key", "license_key"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(String(50), ForeignKey("plans.id"), nullable=False)
    license_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CompanyEntitlement(ControlPlaneBase):
    __tablename__ = "company_entitlements"

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    plan_id: Mapped[str] = mapped_column(String(50), ForeignKey("plans.id"), nullable=False)
    effective_limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    effective_features: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    custom_overrides: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    snapshot_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

Chèn vào `upgrade()` của migration, ngay sau khối `company_memberships` (trước dòng `def downgrade()`):

```python
    # ---- Section 2: Commercial, Plans, Licenses & Entitlements ----
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "default_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default=sa.text("""'{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb"""),
        ),
        sa.Column(
            "default_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default=sa.text(
                """'{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb"""
            ),
        ),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "licenses",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.String(length=50), nullable=False),
        sa.Column("license_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("license_key"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], [f"{CONTROL_PLANE_SCHEMA}.plans.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_licenses_id", "licenses", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_licenses_company", "licenses", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_licenses_key", "licenses", ["license_key"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "company_entitlements",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.String(length=50), nullable=False),
        sa.Column("effective_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "custom_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("snapshot_signature", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("company_id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], [f"{CONTROL_PLANE_SCHEMA}.plans.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
```

Chèn vào đầu `downgrade()` (trước khối `company_memberships` đã có):

```python
    op.drop_table("company_entitlements", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_licenses_key", table_name="licenses", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_licenses_company", table_name="licenses", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_licenses_id", table_name="licenses", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("licenses", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("plans", schema=CONTROL_PLANE_SCHEMA)

```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/models.py backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "feat(control-plane): baseline migration section 2 - plans/licenses/entitlements"
```

---

### Task 5: Baseline migration — Section 3 (Project Registry, đúng tâm điểm drift-fix)

**Files:**
- Modify: `backend/app/platform/control_plane/models.py`
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Consumes: `Company` (Task 3).
- Produces: `ProjectRegistry`, `ProjectStageHistory`, `ProjectOutcome`, `ProjectMetric`.

**Đây là task hiện thực hoá trực tiếp phần drift đã verify cụ thể trong đề xuất**: `projects_registry` bỏ hẳn cột `local_project_snowflake` và constraint `uq_company_project_local` (chỉ có ý nghĩa khi PK trung tâm là UUID, nay PK đã là chính Snowflake nên cột này trở thành trùng lặp vô nghĩa với `id`).

- [ ] **Step 1: Viết test thất bại**

```python
def test_projects_registry_drops_redundant_local_snowflake_column():
    """Regression test cho phat hien drift cu the o Quyet dinh 2: cot
    `local_project_snowflake` va constraint `uq_company_project_local` chi co
    y nghia khi PK trung tam la UUID — phai bi xoa khi PK da la BigInt
    Snowflake."""
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger

tables = ControlPlaneBase.metadata.tables
registry = tables["control_plane.projects_registry"]
assert isinstance(registry.c.id.type, BigInteger)
assert "local_project_snowflake" not in registry.c
assert "uq_company_project_local" not in {c.name for c in registry.constraints}

history = tables["control_plane.project_stage_history"]
assert isinstance(history.c.project_id.type, BigInteger)
assert "metadata_json" in {col.name for col in history.c} or "metadata" in history.c

outcomes = tables["control_plane.project_outcomes"]
assert outcomes.c.project_id.primary_key is True

metrics = tables["control_plane.project_metrics"]
assert metrics.c.project_id.primary_key is True
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `control_plane.projects_registry` chưa tồn tại.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `backend/app/platform/control_plane/models.py`. Lưu ý `metadata` là tên thuộc tính dành riêng của SQLAlchemy Declarative — cột `metadata` trong `project_stage_history` được map qua thuộc tính Python `metadata_json`:

```python
class ProjectRegistry(SnowflakeIDMixin, ControlPlaneBase):
    """Central project registry. KHONG con cot `local_project_snowflake`/
    constraint `uq_company_project_local` — du thua tu khi PK trung tam la
    BigInt Snowflake (Quyet dinh 5), thay vi UUID nhu ban `deploy/central_vps
    /init_central_postgres.sql` cu."""

    __tablename__ = "projects_registry"
    __table_args__ = (
        Index("ix_projects_registry_company", "company_id"),
        Index("ix_projects_registry_stage", "current_stage"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="S0_EXPLORE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_stage_change_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectStageHistory(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "project_stage_history"
    __table_args__ = (
        Index("ix_project_stage_history_project", "project_id"),
        Index("ix_project_stage_history_company", "company_id"),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    duration_seconds: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    change_source: Mapped[Optional[str]] = mapped_column(String(50), default="local_sync")
    # `metadata` la thuoc tinh dung rieng cua SQLAlchemy Declarative — map
    # qua thuoc tinh Python `metadata_json`, ten cot DB van la `metadata`.
    # nullable=True khop nguyen ban SQL goc (`metadata JSONB DEFAULT '{}'::jsonb`,
    # khong co NOT NULL) — phai khai bao dung nullable o day, neu khong
    # `alembic check` o Task 11 se bao lech giua model va migration.
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )


class ProjectOutcome(ControlPlaneBase):
    __tablename__ = "project_outcomes"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    first_interview_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_experiment_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mvp_launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_customer_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_revenue_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    has_revenue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revenue_band: Mapped[Optional[str]] = mapped_column(String(50), default="0")
    team_size_band: Mapped[Optional[str]] = mapped_column(String(50), default="1-2")
    outcome_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class ProjectMetric(ControlPlaneBase):
    __tablename__ = "project_metrics"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    customer_interview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    experiment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validated_assumption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalidated_assumption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lead_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    customer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_campaign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mvp_release_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_metric_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
```

Chèn vào `upgrade()`, sau khối Section 2:

```python
    # ---- Section 3: Project Registry, Stage History & Outcomes ----
    # DRIFT FIX (Quyet dinh 2): KHONG con cot `local_project_snowflake` /
    # constraint `uq_company_project_local` — du thua vi PK trung tam da la
    # chinh no (BigInt Snowflake), khac voi ban UUID cu o deploy/central_vps.
    op.create_table(
        "projects_registry",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("current_stage", sa.String(length=50), nullable=False, server_default="S0_EXPLORE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_stage_change_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_projects_registry_id", "projects_registry", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_projects_registry_company", "projects_registry", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_projects_registry_stage", "projects_registry", ["current_stage"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "project_stage_history",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("from_stage", sa.String(length=50), nullable=True),
        sa.Column("to_stage", sa.String(length=50), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("duration_seconds", sa.BigInteger(), nullable=True),
        sa.Column("change_source", sa.String(length=50), nullable=True, server_default="local_sync"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_project_stage_history_id", "project_stage_history", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_project_stage_history_project", "project_stage_history", ["project_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_project_stage_history_company", "project_stage_history", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "project_outcomes",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("first_interview_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_experiment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mvp_launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_customer_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_revenue_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_revenue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revenue_band", sa.String(length=50), nullable=True, server_default="0"),
        sa.Column("team_size_band", sa.String(length=50), nullable=True, server_default="1-2"),
        sa.Column("outcome_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("project_id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "project_metrics",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_interview_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("experiment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validated_assumption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalidated_assumption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lead_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("customer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_campaign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mvp_release_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_metric_sync_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("project_id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

```

Chèn vào đầu `downgrade()`:

```python
    op.drop_table("project_metrics", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("project_outcomes", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_project_stage_history_company", table_name="project_stage_history", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_project_stage_history_project", table_name="project_stage_history", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_project_stage_history_id", table_name="project_stage_history", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("project_stage_history", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_projects_registry_stage", table_name="projects_registry", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_projects_registry_company", table_name="projects_registry", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_projects_registry_id", table_name="projects_registry", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("projects_registry", schema=CONTROL_PLANE_SCHEMA)

```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/models.py backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "fix(control-plane): drop redundant local_project_snowflake drift in projects_registry"
```

---

### Task 6: Baseline migration — Section 4 (Programs, Cohorts & Ecosystem Intelligence)

**Files:**
- Modify: `backend/app/platform/control_plane/models.py`
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Consumes: `Company`, `ProjectRegistry`, `PlatformUser` (Task 3, 5).
- Produces: `Program`, `Cohort`, `ProgramParticipant`, `ProjectProgramLink`.

- [ ] **Step 1: Viết test thất bại**

```python
def test_ecosystem_tables_use_correct_pk_types():
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import String, BigInteger

tables = ControlPlaneBase.metadata.tables
program = tables["control_plane.programs"]
assert isinstance(program.c.id.type, String)

cohort = tables["control_plane.cohorts"]
assert isinstance(cohort.c.id.type, String)
assert isinstance(cohort.c.program_id.type, String)

participant = tables["control_plane.program_participants"]
assert isinstance(participant.c.id.type, BigInteger)
assert isinstance(participant.c.user_id.type, BigInteger)

link = tables["control_plane.project_program_links"]
assert {c.name for c in link.primary_key.columns} == {"project_id", "cohort_id"}
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `control_plane.programs` chưa tồn tại.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `backend/app/platform/control_plane/models.py`:

```python
class Program(ControlPlaneBase):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_name: Mapped[Optional[str]] = mapped_column(String(255), default="SIHUB")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Cohort(ControlPlaneBase):
    __tablename__ = "cohorts"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(50), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Any] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[Any]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ProgramParticipant(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "program_participants"
    __table_args__ = (
        UniqueConstraint("cohort_id", "company_id", name="uq_cohort_participant"),
        Index("ix_program_participants_cohort", "cohort_id"),
        Index("ix_program_participants_company", "company_id"),
    )

    program_id: Mapped[str] = mapped_column(String(50), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    cohort_id: Mapped[str] = mapped_column(String(100), ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")


class ProjectProgramLink(ControlPlaneBase):
    __tablename__ = "project_program_links"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), primary_key=True
    )
    cohort_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("cohorts.id", ondelete="CASCADE"), primary_key=True
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
```

Chèn vào `upgrade()`, sau khối Section 3:

```python
    # ---- Section 4: Programs, Cohorts & Ecosystem Intelligence ----
    op.create_table(
        "programs",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("partner_name", sa.String(length=255), nullable=True, server_default="SIHUB"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "cohorts",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("program_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["program_id"], [f"{CONTROL_PLANE_SCHEMA}.programs.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "program_participants",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("program_id", sa.String(length=50), nullable=False),
        sa.Column("cohort_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_id", "company_id", name="uq_cohort_participant"),
        sa.ForeignKeyConstraint(["program_id"], [f"{CONTROL_PLANE_SCHEMA}.programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], [f"{CONTROL_PLANE_SCHEMA}.cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_program_participants_id", "program_participants", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_program_participants_cohort", "program_participants", ["cohort_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_program_participants_company", "program_participants", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "project_program_links",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("cohort_id", sa.String(length=100), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("project_id", "cohort_id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], [f"{CONTROL_PLANE_SCHEMA}.cohorts.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

```

Chèn vào đầu `downgrade()`:

```python
    op.drop_table("project_program_links", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_program_participants_company", table_name="program_participants", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_program_participants_cohort", table_name="program_participants", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_program_participants_id", table_name="program_participants", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("program_participants", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("cohorts", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("programs", schema=CONTROL_PLANE_SCHEMA)

```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/models.py backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "feat(control-plane): baseline migration section 4 - programs and cohorts"
```

---

### Task 7: Baseline migration — Section 5 (Marketing & Public Edge Registry, đúng tâm điểm collision-fix)

**Files:**
- Modify: `backend/app/platform/control_plane/models.py`
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Consumes: `Company`, `ProjectRegistry` (Task 3, 5).
- Produces: `CompanyWebApp`, `Domain`, `FormSubmission`, `Deployment` (control-plane).

**Đây là task hiện thực hoá trực tiếp fix va chạm tên bảng đã verify** (`app.platform.core.deployment_models.Deployment` ở Local Business DB dùng `__tablename__ = "deployments"`, schema `public`).

- [ ] **Step 1: Viết test thất bại**

```python
def test_control_plane_deployments_table_does_not_collide_with_local_business_db():
    """Regression test cho va cham ten bang thuc te da verify:
    app.platform.core.deployment_models.Deployment (Local Business DB,
    __tablename__ = 'deployments', schema public) trung ten voi bang
    control-plane 'deployments' (VPS deployment registry). Ca 2 phai la 2
    Table object khac nhau, khac schema, khac cot."""
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from app.db.base import Base as LocalBase  # import day du model Local Business DB

cp_deployments = ControlPlaneBase.metadata.tables["control_plane.deployments"]
local_deployments = LocalBase.metadata.tables["deployments"]

assert cp_deployments is not local_deployments
assert cp_deployments.schema == "control_plane"
assert local_deployments.schema is None  # public (mac dinh)
assert {c.name for c in cp_deployments.c} != {c.name for c in local_deployments.c}
assert "app_id" in cp_deployments.c  # cot rieng cua control-plane
assert "vps_id" in local_deployments.c  # cot rieng cua Local Business DB
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `control_plane.deployments` chưa tồn tại.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `backend/app/platform/control_plane/models.py`:

```python
class CompanyWebApp(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "company_web_apps"

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    app_type: Mapped[str] = mapped_column(String(50), nullable=False, default="marketing")
    repository_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deployment_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="cosa_managed")
    current_version: Mapped[Optional[str]] = mapped_column(String(50), default="v1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Domain(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "domains"
    __table_args__ = (Index("ix_domains_hostname", "hostname"),)

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    app_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company_web_apps.id", ondelete="CASCADE"), nullable=False
    )
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cosa_subdomain")
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="verified")
    ssl_status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class FormSubmission(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "form_submissions"
    __table_args__ = (Index("ix_form_submissions_company_sync", "company_id", "sync_status"),)

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id"), nullable=True
    )
    form_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    sync_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Deployment(SnowflakeIDMixin, ControlPlaneBase):
    """VPS deployment registry cua Central Control Plane. KHONG duoc nham lan
    voi `app.platform.core.deployment_models.Deployment` (Local Business DB,
    schema `public`, cung ten bang `deployments` nhung khac cot hoan toan) —
    day chinh la va cham ten bang thuc te da verify khien plan nay dua toan
    bo bang control-plane vao schema `control_plane` rieng."""

    __tablename__ = "deployments"

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    app_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company_web_apps.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cosa_shared_vps")
    target_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    build_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    deployment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

Chèn vào `upgrade()`, sau khối Section 4:

```python
    # ---- Section 5: Marketing & Public Edge Registry ----
    op.create_table(
        "company_web_apps",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("app_type", sa.String(length=50), nullable=False, server_default="marketing"),
        sa.Column("repository_ref", sa.Text(), nullable=True),
        sa.Column("deployment_mode", sa.String(length=50), nullable=False, server_default="cosa_managed"),
        sa.Column("current_version", sa.String(length=50), nullable=True, server_default="v1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_company_web_apps_id", "company_web_apps", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "domains",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("app_id", sa.BigInteger(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("domain_type", sa.String(length=50), nullable=False, server_default="cosa_subdomain"),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="verified"),
        sa.Column("ssl_status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_id"], [f"{CONTROL_PLANE_SCHEMA}.company_web_apps.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_domains_id", "domains", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_domains_hostname", "domains", ["hostname"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "form_submissions",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("form_slug", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_form_submissions_id", "form_submissions", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index(
        "ix_form_submissions_company_sync", "form_submissions", ["company_id", "sync_status"],
        unique=False, schema=CONTROL_PLANE_SCHEMA,
    )

    # `deployments`: TEN BANG TRUNG voi app.platform.core.deployment_models
    # .Deployment o Local Business DB (schema public) — nam trong schema
    # `control_plane` rieng chinh la fix cho va cham nay.
    op.create_table(
        "deployments",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("app_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False, server_default="cosa_shared_vps"),
        sa.Column("target_ref", sa.Text(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("build_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("deployment_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_id"], [f"{CONTROL_PLANE_SCHEMA}.company_web_apps.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_deployments_id", "deployments", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

```

Chèn vào đầu `downgrade()`:

```python
    op.drop_index("ix_deployments_id", table_name="deployments", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("deployments", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_form_submissions_company_sync", table_name="form_submissions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_form_submissions_id", table_name="form_submissions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("form_submissions", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_domains_hostname", table_name="domains", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_domains_id", table_name="domains", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("domains", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_company_web_apps_id", table_name="company_web_apps", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("company_web_apps", schema=CONTROL_PLANE_SCHEMA)

```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/models.py backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "fix(control-plane): isolate deployments table from Local Business DB collision"
```

---

### Task 8: Baseline migration — Section 6 (Session & Refresh Token Management, bảng bị thiếu)

**Files:**
- Modify: `backend/app/platform/control_plane/models.py`
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/test_control_plane_migration_metadata.py` (bổ sung)

**Interfaces:**
- Consumes: `PlatformUser` (Task 3).
- Produces: `UserSession`.

**Đây là task hiện thực hoá fix "bảng bị rơi mất khi drift"**: `user_sessions` chỉ tồn tại ở `infra/supabase/migrations/...`, hoàn toàn vắng mặt ở `deploy/central_vps/init_central_postgres.sql` dù cả 2 đều tự nhận "Custom JWT Auth".

- [ ] **Step 1: Viết test thất bại**

```python
def test_user_sessions_table_carried_over_from_infra_supabase_only():
    """Regression test: bang nay chi co o infra/supabase/migrations/... (bi
    thieu o deploy/central_vps/init_central_postgres.sql) — phai duoc mang
    sang baseline moi, khong bi mat khi hop nhat."""
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger

tables = ControlPlaneBase.metadata.tables
sessions = tables["control_plane.user_sessions"]
assert isinstance(sessions.c.id.type, BigInteger)
assert isinstance(sessions.c.user_id.type, BigInteger)
assert "refresh_token_hash" in sessions.c
assert "device_info" in sessions.c
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: FAIL — `control_plane.user_sessions` chưa tồn tại.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `backend/app/platform/control_plane/models.py`:

```python
class UserSession(SnowflakeIDMixin, ControlPlaneBase):
    """Session/refresh-token cho Custom JWT Auth. Chi co o
    infra/supabase/migrations/001_initial_central_control_plane.sql —
    deploy/central_vps/init_central_postgres.sql thieu bang nay (drift do bo
    sot, khong phai chu dinh loai bo)."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user", "user_id"),
        Index("ix_user_sessions_token", "refresh_token_hash"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    device_info: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
```

Chèn vào `upgrade()`, sau khối Section 5:

```python
    # ---- Section 6: Session & Refresh Token Management ----
    # Bang nay CHI co o infra/supabase/migrations/... — bi thieu (drift do bo
    # sot) o deploy/central_vps/init_central_postgres.sql. Mang nguyen sang.
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("device_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_user_sessions_id", "user_sessions", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_user_sessions_user", "user_sessions", ["user_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_user_sessions_token", "user_sessions", ["refresh_token_hash"], unique=False, schema=CONTROL_PLANE_SCHEMA)

```

Chèn vào đầu `downgrade()`:

```python
    op.drop_index("ix_user_sessions_token", table_name="user_sessions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_user_sessions_user", table_name="user_sessions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_user_sessions_id", table_name="user_sessions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("user_sessions", schema=CONTROL_PLANE_SCHEMA)

```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/test_control_plane_migration_metadata.py -q`
Expected: PASS — toàn bộ 19 bảng đã có mặt trong `ControlPlaneBase.metadata`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/platform/control_plane/models.py backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/test_control_plane_migration_metadata.py
git commit -m "fix(control-plane): restore user_sessions table missing from central_vps variant"
```

---

### Task 9: Seed data (plans + programs)

**Files:**
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/migrations/test_control_plane_baseline_migration.py`

**Interfaces:**
- Consumes: bảng `plans`/`programs` (Task 4, 6).
- Produces: không có interface Python mới — chỉ dữ liệu seed trong `upgrade()`.

- [ ] **Step 1: Viết test thất bại**

```python
# backend/app/tests/migrations/test_control_plane_baseline_migration.py
"""Test tren chinh source code cua migration baseline (khong can DB that) —
theo mau backend/app/tests/migrations/test_workflow_lifecycle_migration.py
da co san trong repo."""
import importlib.util
from pathlib import Path


def _load_migration():
    migration_path = (
        Path(__file__).resolve().parents[3]
        / "alembic_control_plane"
        / "versions"
        / "c9a1f0b2e3d4_unify_central_control_plane_schema.py"
    )
    spec = importlib.util.spec_from_file_location("control_plane_baseline_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingOperations:
    def __init__(self):
        self.executed_sql = []

    def execute(self, statement):
        self.executed_sql.append(str(statement))

    def __getattr__(self, name):
        # Cac phuong thuc khac (create_table/create_index/drop_table/...) da
        # duoc cac test metadata o Task 3-8 cover gian tiep qua
        # ControlPlaneBase.metadata; o day chi can bat lai loi goi khong xac
        # dinh mot cach ro rang thay vi AttributeError kho hieu.
        def _noop(*args, **kwargs):
            return None
        return _noop


def test_baseline_upgrade_seeds_plans_and_programs():
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.upgrade()

    combined_sql = "\n".join(operations.executed_sql)
    for plan_id in ("free", "starter", "pro", "enterprise"):
        assert f"'{plan_id}'" in combined_sql, f"seed plan '{plan_id}' bi thieu"
    for program_id in ("sihub_incubation", "cosa_founder_fellowship"):
        assert f"'{program_id}'" in combined_sql, f"seed program '{program_id}' bi thieu"
    assert "ON CONFLICT (id) DO NOTHING" in combined_sql
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/migrations/test_control_plane_baseline_migration.py -q`
Expected: FAIL — seed SQL chưa được thêm vào `upgrade()`, `combined_sql` không chứa các plan/program id.

- [ ] **Step 3: Viết implementation**

Chèn vào cuối `upgrade()` (sau khối Section 6, trước dòng cuối hàm):

```python
    # ---- Seed data (mac dinh: free/starter/pro/enterprise + 2 chuong trinh) ----
    op.execute(
        sa.text(
            """
            INSERT INTO control_plane.plans (id, name, description, default_limits, default_features, is_public)
            VALUES
                ('free', 'Free / Learning', 'Danh cho hoc vien, nguoi moi bat dau va chuong trinh vuon uom khoi nghiep',
                 '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb, true),
                ('starter', 'Starter', 'Danh cho cac du an khoi nghiep don le dang giai doan kiem chung thi truong',
                 '{"max_projects": 3, "max_seats": 5, "max_scheduled_agents": 3}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": true, "custom_domain": true}'::jsonb, true),
                ('pro', 'Pro / Scale', 'Danh cho doanh nghiep tang truong can tu dong hoa toan dien',
                 '{"max_projects": 20, "max_seats": 20, "max_scheduled_agents": 10}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": true, "custom_domain": true, "priority_sync": true}'::jsonb, true),
                ('enterprise', 'Enterprise Private', 'Danh cho doanh nghiep lon voi ha tang server rieng biet',
                 '{"max_projects": 999, "max_seats": 999, "max_scheduled_agents": 999}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": true, "custom_domain": true, "private_intake": true}'::jsonb, false)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO control_plane.programs (id, name, partner_name, description)
            VALUES
                ('sihub_incubation', 'Chuong trinh Uom tao SIHUB Startup', 'SIHUB', 'Chuong trinh tang toc khoi nghiep doi moi sang tao ho tro boi SIHUB'),
                ('cosa_founder_fellowship', 'COSA Founder Fellowship 2026', 'COSA', 'Chuong trinh dong hanh xay dung doanh nghiep cung tro ly ao AI')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
```

Chèn vào đầu `downgrade()` (dòng đầu tiên, trước cả khối `deployments`):

```python
    op.execute("DELETE FROM control_plane.programs WHERE id IN ('sihub_incubation', 'cosa_founder_fellowship')")
    op.execute("DELETE FROM control_plane.plans WHERE id IN ('free', 'starter', 'pro', 'enterprise')")

```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && PYTHONPATH=. ../.venv/bin/pytest app/tests/migrations/test_control_plane_baseline_migration.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py backend/app/tests/migrations/test_control_plane_baseline_migration.py
git commit -m "feat(control-plane): seed default plans and programs"
```

---

### Task 10: Xác nhận `downgrade()` chốt đúng thứ tự + test round-trip thật trên Postgres

**Files:**
- Modify: `backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`
- Test: `backend/app/tests/migrations/test_control_plane_baseline_migration.py` (bổ sung)

**Interfaces:**
- Consumes: toàn bộ `upgrade()`/`downgrade()` đã build từ Task 3-9.
- Produces: `alembic -c backend/alembic_control_plane.ini upgrade head` / `downgrade base` chạy sạch trên Postgres thật.

Task này xác nhận dòng cuối `downgrade()` — `op.drop_index("ix_platform_users_status", ...)` → ... → `op.drop_table("platform_users", ...)` → `op.execute(f"DROP SCHEMA IF EXISTS {CONTROL_PLANE_SCHEMA} CASCADE")` — đã có sẵn từ cuối Task 3 và không bị các task sau đè lên (mỗi task chỉ chèn vào **đầu** `downgrade()`, đúng thứ tự phụ thuộc ngược). Bước dưới đây verify bằng 1 test tích hợp thật trên Postgres, gated bởi `RUN_DB_INTEGRATION=1` — đúng quy ước đã có trong repo (`Makefile:backend-integration-test`).

- [ ] **Step 1: Viết test thất bại**

Thêm vào `backend/app/tests/migrations/test_control_plane_baseline_migration.py`:

```python
import os
import subprocess
import sys

import pytest


def _control_plane_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")


@pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1",
    reason="Can RUN_DB_INTEGRATION=1 va TEST_DATABASE_URL toi Postgres that",
)
def test_control_plane_baseline_upgrade_and_downgrade_round_trip_on_real_postgres():
    backend_root = Path(__file__).resolve().parents[3]
    env = {
        **os.environ,
        "PYTHONPATH": str(backend_root),
        "CONTROL_PLANE_DATABASE_URL": _control_plane_database_url(),
    }

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_control_plane.ini", "upgrade", "head"],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    check_tables = subprocess.run(
        [
            sys.executable, "-c",
            """
import os
from sqlalchemy import create_engine, inspect
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401

engine = create_engine(os.environ['CONTROL_PLANE_DATABASE_URL'])
inspector = inspect(engine)
actual = set(inspector.get_table_names(schema='control_plane'))
expected = {t.split('.', 1)[1] for t in ControlPlaneBase.metadata.tables}
missing = expected - actual
assert not missing, f"Bang thieu sau khi upgrade: {missing}"
""",
        ],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert check_tables.returncode == 0, check_tables.stderr

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_control_plane.ini", "downgrade", "base"],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert downgrade.returncode == 0, downgrade.stderr

    check_schema_gone = subprocess.run(
        [
            sys.executable, "-c",
            """
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['CONTROL_PLANE_DATABASE_URL'])
with engine.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'control_plane'")
    ).scalar()
    assert exists is None, "Schema control_plane van con sau downgrade base"
""",
        ],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert check_schema_gone.returncode == 0, check_schema_gone.stderr
```

- [ ] **Step 2: Chạy test, xác nhận FAIL nếu có lỗi thứ tự drop**

Run: `cd backend && TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_test RUN_DB_INTEGRATION=1 PYTHONPATH=. ../.venv/bin/pytest app/tests/migrations/test_control_plane_baseline_migration.py -q`

(Yêu cầu 1 Postgres thật đang chạy, ví dụ `docker compose up -d postgres` ở root repo rồi `createdb -h 127.0.0.1 -U javis javis_test`.) Nếu Task 3-9 đã chèn đúng thứ tự (mỗi task chèn vào **đầu** `downgrade()`), test này PASS ngay ở lần chạy đầu — đây là bước xác nhận, không phải bước sửa lỗi bắt buộc. Nếu FAIL, lỗi thường gặp là do FK constraint chưa drop theo đúng thứ tự ngược phụ thuộc; sửa bằng cách di chuyển dòng `op.drop_table` liên quan lên trước bảng mà nó tham chiếu tới.

- [ ] **Step 3: (Chỉ áp dụng nếu Step 2 FAIL) Sửa thứ tự trong `downgrade()`**

Xác nhận `downgrade()` tuân thủ đúng thứ tự sau (mỗi khối do Task tương ứng chèn vào, liệt kê lại để đối chiếu — không cần gõ lại code nếu Step 2 đã PASS):
1. Xoá seed data (`programs`, `plans`) — Task 9
2. `user_sessions` — Task 8
3. `deployments`, `form_submissions`, `domains`, `company_web_apps` — Task 7
4. `project_program_links`, `program_participants`, `cohorts`, `programs` — Task 6
5. `project_metrics`, `project_outcomes`, `project_stage_history`, `projects_registry` — Task 5
6. `company_entitlements`, `licenses`, `plans` — Task 4
7. `company_memberships`, `companies`, `platform_users` — Task 3
8. `DROP SCHEMA IF EXISTS control_plane CASCADE` — Task 3

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: (lệnh giống Step 2)
Expected: PASS — `alembic upgrade head` tạo đủ 19 bảng trong schema `control_plane`, `alembic downgrade base` xoá sạch kể cả schema.

- [ ] **Step 5: Commit**

```bash
git add backend/app/tests/migrations/test_control_plane_baseline_migration.py
git commit -m "test(control-plane): verify baseline upgrade/downgrade round-trip on real postgres"
```

---

### Task 11: Wiring CI + Makefile — `alembic_control_plane check` chạy song song với local, cùng 1 Postgres, khác schema

**Files:**
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`

**Interfaces:**
- Consumes: `backend/alembic_control_plane.ini` (Task 2), baseline migration hoàn chỉnh (Task 3-10).
- Produces: CI xanh xác nhận `models.py` khớp 100% với migration (autogenerate-diff `alembic check`), chạy trên CÙNG Postgres service với Local Business DB — chứng minh trực tiếp thiết kế cách ly theo schema (Task 1) không va chạm.

- [ ] **Step 1: Xác nhận hành vi hiện tại (characterization, không cần test mới)**

Chạy thử cục bộ để xác nhận `alembic -c backend/alembic_control_plane.ini check` hiện chưa được gọi ở đâu trong CI:

Run: `grep -n "alembic_control_plane" .github/workflows/quality.yml Makefile`
Expected: không có kết quả (0 dòng) — xác nhận đây thực sự là thay đổi mới, không phải trùng lặp.

- [ ] **Step 2: Sửa `Makefile`**

Sửa target `backend-integration-test` (dòng 28-32) từ:

```makefile
backend-integration-test:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for integration tests"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
	DATABASE_URL=$(TEST_DATABASE_URL) RUN_DB_INTEGRATION=1 PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/app/tests -q
```

thành:

```makefile
backend-integration-test:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for integration tests"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini upgrade head
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini check
	DATABASE_URL=$(TEST_DATABASE_URL) RUN_DB_INTEGRATION=1 PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/app/tests -q
```

Sửa target `migration-check` (dòng 44-46) từ:

```makefile
migration-check:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for migration checks"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
```

thành:

```makefile
migration-check:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for migration checks"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini check
```

- [ ] **Step 3: Sửa `.github/workflows/quality.yml`**

Trong job `backend`, chèn 2 bước mới ngay sau bước `alembic -c backend/alembic.ini check` (dòng 32) và trước bước `pytest` (dòng 33):

```yaml
      - run: PYTHONPATH=backend alembic -c backend/alembic_control_plane.ini upgrade head
        env:
          CONTROL_PLANE_DATABASE_URL: postgresql://javis:javis@127.0.0.1:5432/javis_test
      - run: PYTHONPATH=backend alembic -c backend/alembic_control_plane.ini check
        env:
          CONTROL_PLANE_DATABASE_URL: postgresql://javis:javis@127.0.0.1:5432/javis_test
```

Đoạn `steps:` sau khi sửa (dòng 24-36 cũ) đọc như sau:

```yaml
      - run: pip install -r backend/requirements.txt
      - run: mkdir -p test-results
      - run: PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
        env:
          DATABASE_URL: postgresql://javis:javis@127.0.0.1:5432/javis_test
      - run: PYTHONPATH=backend alembic -c backend/alembic.ini check
        env:
          DATABASE_URL: postgresql://javis:javis@127.0.0.1:5432/javis_test
      - run: PYTHONPATH=backend alembic -c backend/alembic_control_plane.ini upgrade head
        env:
          CONTROL_PLANE_DATABASE_URL: postgresql://javis:javis@127.0.0.1:5432/javis_test
      - run: PYTHONPATH=backend alembic -c backend/alembic_control_plane.ini check
        env:
          CONTROL_PLANE_DATABASE_URL: postgresql://javis:javis@127.0.0.1:5432/javis_test
      - run: PYTHONPATH=backend RUN_DB_INTEGRATION=1 DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_test pytest backend/app/tests -q --junitxml=test-results/backend.xml
```

Lưu ý: 2 bước Alembic mới trỏ vào **cùng** `javis_test` database (cùng CI Postgres service, cùng như job hiện có) — không mở thêm service Postgres nào — vì thiết kế schema `control_plane` (Task 1-2) đã đảm bảo không va chạm khi co-locate. Đây chính là bài test thực tế cho thiết kế cách ly.

- [ ] **Step 4: Xác nhận cục bộ**

Run:
```bash
docker compose up -d postgres
createdb -h 127.0.0.1 -U javis javis_ci_check 2>/dev/null || true
DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_ci_check PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini upgrade head
DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_ci_check PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini check
CONTROL_PLANE_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_ci_check PYTHONPATH=backend .venv/bin/alembic -c backend/alembic_control_plane.ini upgrade head
CONTROL_PLANE_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_ci_check PYTHONPATH=backend .venv/bin/alembic -c backend/alembic_control_plane.ini check
```
Expected: cả 4 lệnh exit code 0, không báo "target database is not up to date" hay lỗi trùng bảng `alembic_version`/`deployments`.

- [ ] **Step 5: Commit**

```bash
git add Makefile .github/workflows/quality.yml
git commit -m "ci(control-plane): wire alembic_control_plane upgrade/check into CI and Makefile"
```

---

### Task 12: Cập nhật `backend/Dockerfile.api` để đóng gói Alembic history mới

**Files:**
- Modify: `backend/Dockerfile.api`

**Interfaces:**
- Consumes: `backend/alembic_control_plane/`, `backend/alembic_control_plane.ini` (Task 2-10).
- Produces: image build từ `Dockerfile.api` có sẵn `alembic_control_plane/` để bất kỳ container nào (kể cả service migrate mới ở Task 13-14) chạy được `alembic -c alembic_control_plane.ini upgrade head`.

- [ ] **Step 1: Xác nhận thiếu (characterization)**

Run: `grep -n "alembic_control_plane" backend/Dockerfile.api`
Expected: không có kết quả — xác nhận image hiện tại build từ `Dockerfile.api` sẽ KHÔNG có `alembic_control_plane/` bên trong, nên bất kỳ container nào cố chạy `alembic -c alembic_control_plane.ini upgrade head` sẽ lỗi "file not found".

- [ ] **Step 2: Sửa `backend/Dockerfile.api`**

Từ:
```dockerfile
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

EXPOSE 8000
```

thành:
```dockerfile
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY alembic_control_plane/ ./alembic_control_plane/
COPY alembic_control_plane.ini .

EXPOSE 8000
```

(`CMD` giữ nguyên — image này vẫn chỉ auto-migrate Local Business DB khi boot `uvicorn app.main:app`; migrate control-plane là 1 service riêng chạy `command:` khác, xem Task 13-14, không chạy tự động trong `CMD` này.)

- [ ] **Step 3: Build thử để xác nhận**

Run: `docker build -f backend/Dockerfile.api -t cosa-backend-test backend/`
Expected: build thành công; chạy `docker run --rm cosa-backend-test ls alembic_control_plane` liệt kê ra `env.py`, `script.py.mako`, `versions/`.

- [ ] **Step 4: Xác nhận không phá vỡ hành vi cũ**

Run: `docker run --rm cosa-backend-test alembic -c alembic.ini heads`
Expected: vẫn in ra head hiện tại của Local Business DB (`c6e01c5a0006` hoặc mới hơn) — xác nhận việc thêm COPY không ảnh hưởng tới Alembic history cũ.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile.api
git commit -m "build(control-plane): package alembic_control_plane into backend image"
```

---

### Task 13: `docker-compose.yml` gốc — `migrate-control-plane` chuyển từ raw SQL sang Alembic

**Files:**
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: image build từ `backend/Dockerfile.api` (Task 12).
- Produces: `docker compose --profile control-plane run --rm migrate-control-plane` (đã dùng ở `Makefile:deploy-control-plane`) giờ chạy Alembic thay vì `psql -f infra/supabase/migrations/001_initial_central_control_plane.sql`.

- [ ] **Step 1: Xác nhận hành vi hiện tại (characterization)**

Run: `grep -n "migrate-control-plane" -A 20 docker-compose.yml | head -25`
Expected: thấy service dùng `image: postgres:16-alpine`, mount `./infra/supabase/migrations:/migrations:ro`, entrypoint chạy `psql ... -f /migrations/001_initial_central_control_plane.sql`.

- [ ] **Step 2: Sửa `docker-compose.yml`**

Từ (dòng 59-89):
```yaml
  # ─────────────────────────────────────────────────────────────
  # Central Control Plane Schema Migration
  #
  # HOSTINGER (hiện tại): CONTROL_PLANE_DATABASE_URL trỏ vào postgres
  #   container nội bộ qua Docker internal network.
  #
  # VIETTEL vDBS (tương lai): chỉ cần đổi CONTROL_PLANE_DATABASE_URL
  #   thành connection string của vDBS — không thay đổi gì khác.
  #
  # Cách chạy:
  #   docker compose --profile control-plane up migrate-control-plane
  # ─────────────────────────────────────────────────────────────
  migrate-control-plane:
    image: postgres:16-alpine
    container_name: cosa_migrate_control_plane
    environment:
      # Hostinger: trỏ vào postgres service nội bộ
      # Viettel vDBS: postgresql://user:pass@vdbs-host.viettel.vn:5432/dbname
      - CONTROL_PLANE_DATABASE_URL=${CONTROL_PLANE_DATABASE_URL:-postgresql://${POSTGRES_USER:-javis}:${POSTGRES_PASSWORD:-javis}@postgres:5432/${POSTGRES_DB:-javis}}
    volumes:
      - ./infra/supabase/migrations:/migrations:ro
    entrypoint: >
      sh -c "
        echo '[control-plane] Connecting to: '$$CONTROL_PLANE_DATABASE_URL &&
        psql $$CONTROL_PLANE_DATABASE_URL
             -f /migrations/001_initial_central_control_plane.sql &&
        echo '[control-plane] Migration done.'
      "
    profiles:
      - control-plane
    restart: "no"
```

thành:
```yaml
  # ─────────────────────────────────────────────────────────────
  # Central Control Plane Schema Migration (Alembic — Quyết định 2)
  #
  # HOSTINGER (hiện tại): CONTROL_PLANE_DATABASE_URL trỏ vào postgres
  #   container nội bộ qua Docker internal network.
  #
  # VIETTEL vDBS (tương lai): chỉ cần đổi CONTROL_PLANE_DATABASE_URL
  #   thành connection string của vDBS — không thay đổi gì khác.
  #
  # Trước đây service này chạy raw `psql -f
  # infra/supabase/migrations/001_initial_central_control_plane.sql`. File
  # đó đã được đưa vào Alembic (backend/alembic_control_plane/) và đánh dấu
  # superseded — không còn được áp dụng trực tiếp.
  #
  # Cách chạy:
  #   docker compose --profile control-plane run --rm migrate-control-plane
  # ─────────────────────────────────────────────────────────────
  migrate-control-plane:
    build:
      context: ./backend
      dockerfile: Dockerfile.api
    container_name: cosa_migrate_control_plane
    command: alembic -c alembic_control_plane.ini upgrade head
    environment:
      # Hostinger: trỏ vào postgres service nội bộ
      # Viettel vDBS: postgresql://user:pass@vdbs-host.viettel.vn:5432/dbname
      - CONTROL_PLANE_DATABASE_URL=${CONTROL_PLANE_DATABASE_URL:-postgresql://${POSTGRES_USER:-javis}:${POSTGRES_PASSWORD:-javis}@postgres:5432/${POSTGRES_DB:-javis}}
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
    profiles:
      - control-plane
    restart: "no"
```

- [ ] **Step 3: Xác nhận cục bộ**

Run:
```bash
docker compose up -d postgres
docker compose --profile control-plane run --rm migrate-control-plane
```
Expected: log in ra các dòng `INFO [alembic.runtime.migration] Running upgrade -> c9a1f0b2e3d4`; exit code 0.

- [ ] **Step 4: Xác nhận idempotent (chạy lại lần 2)**

Run: `docker compose --profile control-plane run --rm migrate-control-plane`
Expected: exit code 0, log không báo lỗi (Alembic tự nhận ra đã ở `head`, không làm gì thêm).

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(control-plane): run alembic instead of raw SQL in migrate-control-plane"
```

---

### Task 14: `deploy/central_vps/docker-compose.yaml` — bỏ init SQL, thêm service migrate Alembic

**Files:**
- Modify: `deploy/central_vps/docker-compose.yaml`

**Interfaces:**
- Consumes: image build từ `backend/Dockerfile.api` (Task 12) — build context giữ nguyên `../../backend` như `central_api` đã dùng.
- Produces: service `central_postgres` không còn tự động chạy `init_central_postgres.sql` khi khởi tạo volume trống; service mới `migrate_control_plane` chạy Alembic; `central_api` chỉ khởi động sau khi migrate xong.

**Lưu ý phạm vi**: task này CHỈ sửa cơ chế áp dụng schema (`central_postgres`'s init mount + thêm service migrate). KHÔNG sửa `command`/biến `APP_ROLE` của `central_api` — đó là phạm vi Quyết định 3 (đang được plan khác thực hiện song song).

- [ ] **Step 1: Xác nhận hành vi hiện tại (characterization)**

Run: `grep -n "init_central_postgres.sql\|docker-entrypoint-initdb" deploy/central_vps/docker-compose.yaml`
Expected: 1 dòng — `- ./init_central_postgres.sql:/docker-entrypoint-initdb.d/init.sql` trong service `central_postgres`.

- [ ] **Step 2: Sửa `deploy/central_vps/docker-compose.yaml`**

Từ (service `central_postgres`, dòng 43-57):
```yaml
  central_postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-cosa_central}
      POSTGRES_USER: ${POSTGRES_USER:-cosa_central_admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-SecureCentralPass2026}
    volumes:
      - central_pgdata:/var/lib/postgresql/data
      - ./init_central_postgres.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-cosa_central_admin} -d ${POSTGRES_DB:-cosa_central}" ]
      interval: 5s
      timeout: 5s
      retries: 5
```

thành (bỏ dòng mount SQL — Alembic đảm nhiệm việc tạo schema, xem service mới `migrate_control_plane` bên dưới):
```yaml
  central_postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-cosa_central}
      POSTGRES_USER: ${POSTGRES_USER:-cosa_central_admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-SecureCentralPass2026}
    volumes:
      - central_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-cosa_central_admin} -d ${POSTGRES_DB:-cosa_central}" ]
      interval: 5s
      timeout: 5s
      retries: 5

  # ============================================================================
  # 2b. Central Control Plane Schema Migration (Alembic — Quyết định 2)
  # Trước đây central_postgres tự áp init_central_postgres.sql (PK kiểu UUID)
  # qua docker-entrypoint-initdb.d. File đó đã bị loại bỏ về mặt PK (chốt
  # BigInt Snowflake) và đánh dấu superseded — schema giờ áp bằng Alembic.
  # ============================================================================
  migrate_control_plane:
    build:
      context: ../../backend
      dockerfile: Dockerfile.api
    restart: "no"
    command: alembic -c alembic_control_plane.ini upgrade head
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-cosa_central_admin}:${POSTGRES_PASSWORD:-SecureCentralPass2026}@central_postgres:5432/${POSTGRES_DB:-cosa_central}
    depends_on:
      central_postgres:
        condition: service_healthy
```

Sửa `depends_on` của `central_api` (dòng 36-38) từ:
```yaml
    depends_on:
      central_postgres:
        condition: service_healthy
```

thành:
```yaml
    depends_on:
      central_postgres:
        condition: service_healthy
      migrate_control_plane:
        condition: service_completed_successfully
```

- [ ] **Step 3: Xác nhận cục bộ**

Run:
```bash
cd deploy/central_vps
cp .env.example .env
docker compose up -d --build central_postgres migrate_control_plane
docker compose logs migrate_control_plane
```
Expected: log `migrate_control_plane` in ra `Running upgrade -> c9a1f0b2e3d4`, container exit 0 (không phải `restart: always` nên tự dừng sau khi chạy xong).

- [ ] **Step 4: Xác nhận `central_api` chờ đúng thứ tự**

Run: `docker compose up -d`
Expected: `central_api` khởi động sau khi `migrate_control_plane` hoàn tất thành công (`docker compose ps` cho thấy `migrate_control_plane` ở trạng thái `exited (0)` trước khi `central_api` chuyển sang `running`).

- [ ] **Step 5: Commit**

```bash
git add deploy/central_vps/docker-compose.yaml
git commit -m "feat(control-plane): replace init SQL mount with alembic migration service in central_vps compose"
```

---

### Task 15: Đánh dấu superseded 2 file SQL gốc (không xoá)

**Files:**
- Modify: `infra/supabase/migrations/001_initial_central_control_plane.sql`
- Modify: `deploy/central_vps/init_central_postgres.sql`

**Interfaces:**
- Không có interface code — chỉ header comment, theo đúng convention retire đã có ở Quyết định 6.2 của đề xuất gốc ("Cần 1 ghi chú 'superseded by tài liệu này' ở đầu file, không xoá thẳng").

- [ ] **Step 1: Xác nhận chưa có ghi chú superseded (characterization)**

Run: `grep -n "SUPERSEDE\|superseded" infra/supabase/migrations/001_initial_central_control_plane.sql deploy/central_vps/init_central_postgres.sql`
Expected: không có kết quả.

- [ ] **Step 2: Thêm header vào `infra/supabase/migrations/001_initial_central_control_plane.sql`**

Chèn ngay sau khối comment tiêu đề hiện có (sau dòng 6, trước dòng 7 `-- 0. EXTENSIONS`... thực ra trước dòng `CREATE EXTENSION` dòng 9, tức chèn giữa dòng 6 và dòng 8):

```sql
-- ============================================================================
-- ĐÃ SUPERSEDE (2026-08-21): Schema này đã được đưa vào Alembic tại
-- backend/alembic_control_plane/ (baseline:
-- c9a1f0b2e3d4_unify_central_control_plane_schema.py). File SQL này KHÔNG
-- còn được áp dụng trực tiếp — docker-compose.yml (service
-- migrate-control-plane) đã đổi sang `alembic -c alembic_control_plane.ini
-- upgrade head`. Giữ lại file này chỉ để tham khảo lịch sử quyết định
-- (docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md, Quyết định 2).
--
-- Toàn bộ bảng + seed data ở file này đã được port nguyên vẹn vào baseline
-- Alembic, TRỪ: cột `local_project_snowflake` và constraint
-- `uq_company_project_local` ở `projects_registry` (đã xoá — dư thừa khi PK
-- trung tâm chính là BigInt Snowflake); và mọi bảng đã chuyển vào schema
-- Postgres `control_plane` thay vì `public` (tránh trùng tên bảng với Local
-- Business DB — cụ thể là bảng `deployments`, xem
-- app/platform/core/deployment_models.py).
-- ============================================================================
```

- [ ] **Step 3: Thêm header vào `deploy/central_vps/init_central_postgres.sql`**

Chèn ngay sau khối comment tiêu đề hiện có (sau dòng 6, trước dòng 8 `CREATE EXTENSION "uuid-ossp"`):

```sql
-- ============================================================================
-- ĐÃ SUPERSEDE (2026-08-21): PK kiểu UUID ở file này đã bị loại bỏ. Theo
-- Quyết định 5 (docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md)
-- toàn bộ dự án giữ thuần Snowflake BigInt ID, không dùng UUID. Nguồn sự
-- thật hiện tại là Alembic tại backend/alembic_control_plane/ — đã port từ
-- infra/supabase/migrations/001_initial_central_control_plane.sql (bản
-- BigInt Snowflake), KHÔNG phải từ file UUID này.
--
-- File này KHÔNG còn được docker-entrypoint-initdb.d áp dụng (xem
-- deploy/central_vps/docker-compose.yaml, service `migrate_control_plane`
-- chạy Alembic thay vì mount file này). Giữ lại chỉ để tham khảo lịch sử.
--
-- CẢNH BÁO VẬN HÀNH: deploy/central_vps/README.md mô tả 1 quy trình deploy
-- thủ công qua Coolify (domain api.vutasoft.com) từng dùng chính file này để
-- khởi tạo database — CHƯA xác nhận được liệu quy trình đó đã thực sự chạy
-- với dữ liệu thật hay chưa. Nếu instance đó tồn tại và có dữ liệu, các bảng
-- ở đó đang dùng PK kiểu UUID — KHÔNG tương thích thẳng với schema Alembic
-- mới (PK BigInt). TUYỆT ĐỐI KHÔNG chạy `alembic upgrade head` (từ
-- backend/alembic_control_plane/) nhắm thẳng vào 1 database đã có dữ liệu
-- theo file này mà chưa có kế hoạch migrate dữ liệu riêng — cần founder xác
-- nhận trạng thái instance đó trước.
-- ============================================================================
```

- [ ] **Step 4: Xác nhận**

Run: `grep -n "SUPERSEDE" infra/supabase/migrations/001_initial_central_control_plane.sql deploy/central_vps/init_central_postgres.sql`
Expected: mỗi file 1 dòng match. Xác nhận cả 2 file KHÔNG bị xoá nội dung gốc bên dưới header mới (chỉ chèn thêm, không xoá dòng cũ nào):

Run: `git diff --stat infra/supabase/migrations/001_initial_central_control_plane.sql deploy/central_vps/init_central_postgres.sql`
Expected: chỉ có dòng thêm (`+`), không có dòng xoá (`-`) nào ngoài các dòng trắng liền kề chỗ chèn (nếu có).

- [ ] **Step 5: Commit**

```bash
git add infra/supabase/migrations/001_initial_central_control_plane.sql deploy/central_vps/init_central_postgres.sql
git commit -m "docs(control-plane): mark legacy control-plane SQL files as superseded by Alembic"
```

---

## Acceptance Criteria (đối chiếu cuối)

- [ ] `backend/app/platform/control_plane/models.py` định nghĩa đủ 19 bảng, tất cả PK kiểu Snowflake BigInt (trừ `plans`/`programs`/`cohorts` dùng business key VARCHAR như nguyên bản, và `project_program_links` dùng composite PK) — không bảng nào dùng UUID.
- [ ] `projects_registry` không còn cột `local_project_snowflake`/constraint `uq_company_project_local`.
- [ ] Bảng `user_sessions` có mặt trong baseline (carried từ `infra/supabase`, vốn thiếu ở `central_vps`).
- [ ] Toàn bộ 19 bảng nằm trong schema Postgres `control_plane`, không phải `public` — verify bằng test collision với `app.platform.core.deployment_models.Deployment`.
- [ ] `alembic -c backend/alembic_control_plane.ini upgrade head` rồi `downgrade base` chạy sạch trên Postgres thật, không lỗi.
- [ ] `alembic -c backend/alembic_control_plane.ini check` xanh trong CI, chạy trên CÙNG Postgres service với `alembic -c backend/alembic.ini check` (Local Business DB) mà không va chạm.
- [ ] `docker compose --profile control-plane run --rm migrate-control-plane` (root) chạy Alembic, không còn `psql -f .../001_initial_central_control_plane.sql`.
- [ ] `deploy/central_vps/docker-compose.yaml`: `central_postgres` không còn tự động áp `init_central_postgres.sql`; service `migrate_control_plane` mới chạy Alembic; `central_api` chờ migrate xong mới khởi động.
- [ ] Cả 2 file SQL gốc còn nguyên trên đĩa, có header "ĐÃ SUPERSEDE" trỏ về Alembic history mới, `init_central_postgres.sql` có thêm cảnh báo về khả năng đã deploy dữ liệu thật.
- [ ] Không file/model nào thuộc `PlatformOutbox`/`PlatformInbox`/`LocalEntitlementSnapshot`/`EntitlementManager`/`PlatformSyncWorker` bị sửa.
- [ ] Không đụng `APP_ROLE`/`create_app`/`central_main.py`/`full_main.py` (Quyết định 3).

## Rủi ro còn tồn đọng sau plan này (KHÔNG xử lý trong phạm vi — cần task/plan riêng)

1. **`entitlement_crypto.py`/`outbox_service.py` gọi `uuid.UUID(company_id)` thật** — sẽ ném lỗi nếu nhận `company_id` dạng Snowflake BigInt từ 1 Central instance đã chạy schema mới. Cần 1 plan riêng để đổi các hàm này sang chấp nhận chuỗi số Snowflake, sau khi có xác nhận không phá vỡ dữ liệu đã đồng bộ trước đó.
2. **Khả năng `api.vutasoft.com` đã được khởi tạo thật với PK UUID** qua Coolify — cần founder xác nhận trạng thái instance này trước khi bất kỳ ai chạy `alembic upgrade head` (control-plane) nhắm vào nó.
3. **`CONTROL_PLANE_DATABASE_URL` mặc định vẫn trỏ chung 1 database với Local Business DB** trên Hostinger — plan này giảm rủi ro va chạm bằng schema `control_plane`, nhưng KHÔNG tách 2 DB thành 2 instance vật lý riêng (đó là quyết định topology/hạ tầng, thuộc phạm vi Quyết định 3 hoặc 1 ADR riêng).
4. **`make boundary-check` khả năng đang đỏ** do quy tắc cấm `uuid\.` quá rộng (bắt cả `uuid.uuid4()` sinh token, không riêng PK). Không thuộc phạm vi Quyết định 2 — models/migration mới của plan này không thêm bất kỳ `uuid.` nào nên không làm tình trạng này xấu thêm, nhưng plan này cũng không sửa được nó.
