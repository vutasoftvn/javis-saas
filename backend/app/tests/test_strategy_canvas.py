from app.core.snowflake import generate_snowflake_id
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.tenancy import get_canvas_scoped, get_evidence_items_scoped, get_revision_scoped
from app.founder_os.strategy.strategy_canvas_service import StrategyCanvasService

# Giới hạn hạ tầng test hiện có (giống app/tests/test_vault.py): repo chưa có
# TestClient/DB test thật, chỉ có MagicMock cho Session. Các test dưới đây phủ invariant
# ở tầng service/Python; CHECK constraint và unique partial index ở tầng DB (đã verify
# thủ công bằng `alembic upgrade head` chạy sạch trên Postgres dev) không thể phủ lại
# bằng unit test mock - cần integration test với DB thật ở phase sau.


def make_service(role: str = "admin") -> tuple[StrategyCanvasService, MagicMock]:
    db = MagicMock()
    service = StrategyCanvasService(db=db, user_id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), role=role)
    return service, db


def mock_revision(status: str = "draft", canvas_id=None):
    revision = MagicMock()
    revision.id = generate_snowflake_id()
    revision.canvas_id = canvas_id or generate_snowflake_id()
    revision.status = status
    return revision


def stub_get_revision(db: MagicMock, revision):
    """get_revision_scoped dùng db.query(StrategyRevision).join(...).filter(...).first()."""
    db.query.return_value.join.return_value.filter.return_value.first.return_value = revision


# ---------------------------------------------------------------------------
# Foundation 1-1-3 invariants
# ---------------------------------------------------------------------------

def _valid_values():
    return [
        {"slot_no": 1, "title": "Minh bạch", "description": "Rõ ràng với khách hàng", "decision_rule": "Không công bố số liệu chưa có nguồn"},
        {"slot_no": 2, "title": "Tốc độ", "description": "Ưu tiên hành động nhanh", "decision_rule": "Chọn phương án triển khai được trong tuần"},
        {"slot_no": 3, "title": "Kỷ luật", "description": "Giữ đúng cam kết", "decision_rule": "Không nhận thêm việc ngoài Big 3 tuần"},
    ]


def test_save_foundation_rejects_wrong_number_of_core_values():
    service, db = make_service()
    stub_get_revision(db, mock_revision("draft"))
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "V" * 30, "M" * 30, _valid_values()[:2])
    assert exc.value.status_code == 422


def test_save_foundation_rejects_duplicate_slot_no():
    service, db = make_service()
    stub_get_revision(db, mock_revision("draft"))
    values = _valid_values()
    values[1]["slot_no"] = 1  # trùng slot 1
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "V" * 30, "M" * 30, values)
    assert exc.value.status_code == 422


def test_save_foundation_rejects_missing_decision_rule():
    service, db = make_service()
    stub_get_revision(db, mock_revision("draft"))
    values = _valid_values()
    values[0]["decision_rule"] = "   "
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "V" * 30, "M" * 30, values)
    assert exc.value.status_code == 422


def test_save_foundation_rejects_vision_too_short():
    service, db = make_service()
    stub_get_revision(db, mock_revision("draft"))
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "quá ngắn", "M" * 30, _valid_values())
    assert exc.value.status_code == 422


def test_save_foundation_rejects_vision_too_long():
    service, db = make_service()
    stub_get_revision(db, mock_revision("draft"))
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "V" * 501, "M" * 30, _valid_values())
    assert exc.value.status_code == 422


def test_save_foundation_locked_when_revision_in_review():
    service, db = make_service()
    stub_get_revision(db, mock_revision("in_review"))
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "V" * 30, "M" * 30, _valid_values())
    assert exc.value.status_code == 409


def test_save_foundation_locked_when_revision_approved():
    service, db = make_service()
    stub_get_revision(db, mock_revision("approved"))
    with pytest.raises(HTTPException) as exc:
        service.save_foundation(generate_snowflake_id(), "V" * 30, "M" * 30, _valid_values())
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Permission gating (owner không bao giờ được gán thực tế -> ngưỡng là "admin")
# ---------------------------------------------------------------------------

def test_approve_revision_requires_admin_role():
    service, _db = make_service(role="editor")
    with pytest.raises(HTTPException) as exc:
        service.approve_revision(generate_snowflake_id())
    assert exc.value.status_code == 403


def test_approve_context_pack_requires_admin_role():
    service, _db = make_service(role="editor")
    with pytest.raises(HTTPException) as exc:
        service.approve_context_pack(generate_snowflake_id())
    assert exc.value.status_code == 403


def test_approve_revision_allowed_for_admin_role_permission_gate():
    # Chỉ assert permission gate không chặn "admin" (không assert toàn bộ luồng DB) -
    # nếu check_permission raise, test này sẽ fail ngay ở bước gọi.
    service, db = make_service(role="admin")
    revision = mock_revision("in_review")
    stub_get_revision(db, revision)
    db.query.return_value.filter.return_value.first.return_value = None  # không có revision approved cũ
    service.approve_revision(revision.id)
    assert revision.status == "approved"


def test_submit_review_requires_editor_role():
    service, _db = make_service(role="viewer")
    with pytest.raises(HTTPException) as exc:
        service.submit_review(generate_snowflake_id())
    assert exc.value.status_code == 403


def test_create_evidence_does_not_require_elevated_role():
    service, db = make_service(role="viewer")
    item = service.create_evidence(
        title="Phỏng vấn khách hàng A",
        summary="Khách hàng cần tích hợp Zalo",
        source_type="customer_interview",
        reliability="medium",
    )
    assert item.title == "Phỏng vấn khách hàng A"
    db.commit.assert_called()


# ---------------------------------------------------------------------------
# approve_revision: thứ tự supersede-cũ-trước-approve-mới
# ---------------------------------------------------------------------------

def test_approve_revision_supersedes_previous_approved_in_order():
    service, db = make_service(role="admin")
    canvas_id = generate_snowflake_id()
    revision = mock_revision("in_review", canvas_id=canvas_id)
    previous_approved = mock_revision("approved", canvas_id=canvas_id)

    stub_get_revision(db, revision)
    db.query.return_value.filter.return_value.first.return_value = previous_approved

    snapshot = {}

    def capture_on_flush():
        # Ghi lại trạng thái previous_approved tại đúng thời điểm flush() đầu tiên
        # được gọi - phải là "superseded" TRƯỚC KHI revision mới được set "approved".
        if "previous_status_at_flush" not in snapshot:
            snapshot["previous_status_at_flush"] = previous_approved.status
            snapshot["new_status_at_flush"] = revision.status

    db.flush.side_effect = capture_on_flush

    service.approve_revision(revision.id)

    assert snapshot["previous_status_at_flush"] == "superseded"
    assert snapshot["new_status_at_flush"] == "in_review"  # chưa bị đổi tại thời điểm flush cũ
    assert revision.status == "approved"
    assert previous_approved.status == "superseded"


def test_approve_revision_rejects_when_not_in_review():
    service, db = make_service(role="admin")
    revision = mock_revision("draft")
    stub_get_revision(db, revision)
    with pytest.raises(HTTPException) as exc:
        service.approve_revision(revision.id)
    assert exc.value.status_code == 409


def test_submit_review_rejects_incomplete_foundation():
    service, db = make_service(role="editor")
    revision = mock_revision("draft")
    stub_get_revision(db, revision)
    # StrategyFoundation query (không qua join) -> None nghĩa là chưa có foundation.
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        service.submit_review(revision.id)
    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Cross-tenant scoping (không lộ thông tin: luôn 404, không phân biệt lý do)
# ---------------------------------------------------------------------------

def test_get_canvas_cross_tenant_returns_404():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_canvas_scoped(db, generate_snowflake_id(), generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_revision_cross_tenant_returns_404():
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_revision_scoped(db, generate_snowflake_id(), generate_snowflake_id())
    assert exc.value.status_code == 404


def test_link_evidence_cross_tenant_evidence_raises_404_without_partial_link():
    # Gửi 2 evidence_id nhưng chỉ 1 cái thực sự thuộc workspace -> toàn bộ request
    # phải 404, không được link một phần (đúng nguyên tắc get_evidence_items_scoped).
    db = MagicMock()
    only_one_item = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [only_one_item]
    with pytest.raises(HTTPException) as exc:
        get_evidence_items_scoped(db, [generate_snowflake_id(), generate_snowflake_id()], generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_evidence_items_scoped_returns_all_when_all_match():
    db = MagicMock()
    ids = [generate_snowflake_id(), generate_snowflake_id()]
    items = [MagicMock(id=i) for i in ids]
    db.query.return_value.filter.return_value.all.return_value = items
    result = get_evidence_items_scoped(db, ids, generate_snowflake_id())
    assert result == items
