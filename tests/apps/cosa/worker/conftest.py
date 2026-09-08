"""Fixture cách ly cho các test lease/crash-recovery THẬT (Postgres +
`services/cosa` Encore thật qua OS process) tại `tests/apps/cosa/worker/`.

Task 7 (plan `2026-09-08-platform-authority-durability-hardening`): các file
`test_lease_mutual_exclusion_real.py` / `test_crash_recovery_subprocess.py`
trước đây tự khai fixture DSN/service riêng, fallback qua một chuỗi biến môi
trường (`COSA_TEST_DATABASE_URL` → `COSA_DATABASE_URL` → `AGENT_TEST_DATABASE_URL`
→ `DATABASE_URL`) và spawn `encore run --port=4000` — cổng CỐ ĐỊNH có thể trùng
với `services/cosa` dev đang chạy sẵn trên máy, và health check chỉ xác nhận
"có gì đó" trả 2xx/5xx ở `:4000`, không xác nhận đó CHÍNH LÀ tiến trình test
vừa spawn. Module này thay bằng:

1. `disposable_cluster` — mỗi test 1 database Postgres riêng (suffix run_id
   ngẫu nhiên), tạo bằng `create_disposable_cluster()` + áp migration thật,
   DROP ở teardown. KHÔNG fallback sang `DATABASE_URL`/`.env` của máy dev.
2. `control_plane_service` — spawn MỘT MÌNH `services/cosa` (Encore) trên cổng
   `pick_free_port()` reserve riêng (không bao giờ `:4000` cố định) trỏ vào
   `disposable_cluster`. Ngay trước khi yield, kiểm tra CẢ HAI: (a) health
   endpoint trả 200/503 — đã có trong `wait_until_ready()`, VÀ (b) tiến trình
   con vừa spawn còn sống (`proc.popen.poll() is None`) — bằng chứng response
   khỏe mạnh đến từ CHÍNH tiến trình test này vừa khởi, không phải một
   `services/cosa` cũ tình cờ đã lắng nghe ở cổng đó từ trước. Vì cổng được
   reserve ngẫu nhiên qua `pick_free_port()`, việc đụng cổng với service cũ đã
   gần như không thể xảy ra — kiểm tra PID sống đóng nốt khe hở còn lại.

`LEASE_INTEGRATION_TEST=1` (đặt bởi `make lease-integration-test`) quyết định
skip hay fail cứng khi Postgres admin không reachable: target unit
(`make apps-cosa-test`) được PHÉP skip (không yêu cầu Postgres — CLAUDE.md quy
tắc kiểm thử), còn target integration chuyên biệt KHÔNG được silently skip.
"""

from __future__ import annotations

import os
import secrets
import shutil
from collections.abc import Iterator

import pytest

from tests.e2e.stack._process import terminate_all
from tests.e2e.stack.disposable_postgres import (
    DisposableCluster,
    apply_migrations,
    create_disposable_cluster,
    drop_disposable_cluster,
)
from tests.e2e.stack.subprocess_stack import asyncpg_test_url, boot_cosa_only

_REQUIRE_REAL_POSTGRES_ENV = "LEASE_INTEGRATION_TEST"


@pytest.fixture
def disposable_cluster() -> Iterator[DisposableCluster]:
    """Database Postgres riêng cho MỖI test — không tái dùng cluster giữa các
    test để tránh 1 test rò rỉ state ảnh hưởng test khác chạy song song."""
    run_id = f"lease{secrets.token_hex(4)}"
    require_real = os.environ.get(_REQUIRE_REAL_POSTGRES_ENV) == "1"
    try:
        cluster = create_disposable_cluster(run_id)
    except Exception as err:  # pragma: no cover - defensive, phụ thuộc môi trường
        message = (
            f"Không tạo được disposable Postgres cluster ({err}). Cần Postgres admin "
            "reachable qua PGHOST/PGPORT/PGUSER/PGPASSWORD (xem "
            "tests/e2e/stack/disposable_postgres.py::_ADMIN)."
        )
        if require_real:
            pytest.fail(message)
        pytest.skip(message)
        return

    try:
        apply_migrations(cluster)
        yield cluster
    finally:
        drop_disposable_cluster(cluster)


@pytest.fixture
def control_plane_dsn(disposable_cluster: DisposableCluster) -> str:
    """DSN libpq của database `cosa` riêng cluster này (Encore/`node-postgres`
    ăn `sslmode` bình thường, không cần strip)."""
    return disposable_cluster.cosa_app_url


@pytest.fixture
def async_control_plane_dsn(control_plane_dsn: str) -> str:
    """DSN asyncpg cho SQLAlchemy — strip `sslmode` qua normalizer dùng chung."""
    return asyncpg_test_url(control_plane_dsn)


@pytest.fixture
def agent_dsn(disposable_cluster: DisposableCluster) -> str:
    """DSN asyncpg của database `agent` riêng cluster này (crash-recovery test
    cần bảng `agent_conversation.conversations`)."""
    return asyncpg_test_url(disposable_cluster.agent_app_url)


@pytest.fixture
def control_plane_service(disposable_cluster: DisposableCluster) -> Iterator[str]:
    """Spawn `services/cosa` (Encore) thật trên cổng reserve riêng, trỏ vào
    `disposable_cluster`. Dưới `make lease-integration-test`
    (`LEASE_INTEGRATION_TEST=1`) thiếu `encore` CLI hoặc tiến trình chết trước
    khi khỏe phải FAIL cứng — không được im lặng bỏ qua; dưới target unit
    (`make apps-cosa-test`, không set biến này) vẫn được skip vì đó là gate
    "không cần Postgres/Encore"."""
    if not shutil.which("encore"):
        message = "`encore` CLI not found on PATH — cần cài để boot services/cosa thật."
        if os.environ.get(_REQUIRE_REAL_POSTGRES_ENV) == "1":
            pytest.fail(message)
        pytest.skip(message)

    base_url, proc = boot_cosa_only(disposable_cluster)
    # Khép khe hở cuối: health đã xanh (wait_until_ready) nhưng phải CHÍNH tiến
    # trình vừa spawn còn sống ngay trước khi test dùng nó — không phải service
    # cũ tình cờ nghe hộ ở cổng vừa reserve.
    assert proc.popen.poll() is None, (
        f"[cosa] tiến trình vừa spawn đã chết ngay sau health check xanh:\n{proc.tail()}"
    )
    try:
        yield base_url
    finally:
        terminate_all([proc])
