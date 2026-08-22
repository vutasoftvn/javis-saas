"""`/sync/ingest`, `/sync/outbox/trigger`, `/sync/status` từng không có xác
thực nào (Depends(get_db) only) - bất kỳ ai gọi được endpoint cũng kích hoạt
được. Test này khoá lại: cần InstallCredential hợp lệ."""
from unittest.mock import MagicMock
import inspect

from platform_core.control_plane.models import InstallCredential
import platform_core.sync.router as sync_router_module


def _credential() -> InstallCredential:
    return MagicMock(spec=InstallCredential)


def test_ingest_requires_install_credential_param():
    sig = inspect.signature(sync_router_module.ingest_platform_events)
    assert "install" in sig.parameters


def test_outbox_trigger_requires_install_credential_param():
    sig = inspect.signature(sync_router_module.trigger_outbox_sync)
    assert "install" in sig.parameters


def test_sync_status_requires_install_credential_param():
    sig = inspect.signature(sync_router_module.get_sync_status)
    assert "install" in sig.parameters


def test_ingest_still_works_with_credential():
    db = MagicMock()
    payload = sync_router_module.IngestBatchRequest(events=[])
    result = sync_router_module.ingest_platform_events(
        payload=payload, db=db, install=_credential()
    )
    assert result.status == "ok"
