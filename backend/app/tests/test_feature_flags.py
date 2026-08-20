from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest

from app.platform.core.models import FeatureFlag
from app.core.auth import get_current_workspace_member
from app.db.session import get_db
from app.db.models import WorkspaceMember
from app.main import app
from app.core.feature_flags import (
    is_enabled,
    set_feature_flag,
    list_feature_flags,
    FLAG_PROJECT_CLASSIFIER_V12,
    FLAG_CYCLE_13WEEK_V12,
    FLAG_MILESTONES_GATES_V12,
    V13_FEATURE_FLAGS,
    V13_DEFAULT_DISABLED_FEATURE_FLAGS,
    V13_DEFAULT_ENABLED_FEATURE_FLAGS,
    effective_feature_flags,
    canonical_flag_key,
)


def test_is_enabled_default_false_when_no_flag():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    assert is_enabled(db, "unknown_flag") is False
    assert is_enabled(db, FLAG_PROJECT_CLASSIFIER_V12, workspace_id=generate_snowflake_id()) is False


def test_is_enabled_global_flag():
    db = MagicMock()
    global_flag = FeatureFlag(
        id=generate_snowflake_id(),
        workspace_id=None,
        key=FLAG_PROJECT_CLASSIFIER_V12,
        enabled=True,
    )
    # When query by workspace_id returns None, fallback query returns global_flag
    ws_query_mock = MagicMock()
    ws_query_mock.first.return_value = None

    global_query_mock = MagicMock()
    global_query_mock.first.return_value = global_flag

    def filter_side_effect(*args, **kwargs):
        # If filtering with workspace_id, return ws_query_mock, else global_query_mock
        return global_query_mock

    db.query.return_value.filter.side_effect = filter_side_effect

    # Global lookup with workspace_id=None
    assert is_enabled(db, FLAG_PROJECT_CLASSIFIER_V12) is True


def test_is_enabled_workspace_override():
    ws_id = generate_snowflake_id()
    ws_flag = FeatureFlag(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        key=FLAG_CYCLE_13WEEK_V12,
        enabled=True,
    )

    db = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = ws_flag
    db.query.return_value.filter.return_value = filter_mock

    assert is_enabled(db, FLAG_CYCLE_13WEEK_V12, workspace_id=ws_id) is True


def test_set_feature_flag_creates_new():
    db = MagicMock()
    # Mock chaining query.filter.filter.first -> None
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

    flag = set_feature_flag(
        db,
        key=FLAG_MILESTONES_GATES_V12,
        enabled=True,
        description="Milestones and gates support",
    )

    assert flag.key == FLAG_MILESTONES_GATES_V12
    assert flag.enabled is True
    assert flag.description == "Milestones and gates support"
    assert db.add.called
    assert db.commit.called
    assert db.refresh.called


def test_set_feature_flag_updates_existing():
    existing_flag = FeatureFlag(
        id=generate_snowflake_id(),
        workspace_id=None,
        key=FLAG_PROJECT_CLASSIFIER_V12,
        enabled=False,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = existing_flag

    flag = set_feature_flag(
        db,
        key=FLAG_PROJECT_CLASSIFIER_V12,
        enabled=True,
        description="Updated description",
    )

    assert flag.enabled is True
    assert flag.description == "Updated description"
    assert not db.add.called
    assert db.commit.called
    assert db.refresh.called


def test_v13_feature_flag_catalog_is_centralized_and_disabled_by_default():
    """V13-only surfaces have one authoritative key and conservative defaults."""
    assert set(V13_DEFAULT_DISABLED_FEATURE_FLAGS) == {"organization_chart"}
    assert set(V13_DEFAULT_ENABLED_FEATURE_FLAGS) == V13_FEATURE_FLAGS - {"organization_chart"}
    assert set(V13_DEFAULT_ENABLED_FEATURE_FLAGS).isdisjoint(V13_DEFAULT_DISABLED_FEATURE_FLAGS)
    assert V13_FEATURE_FLAGS == {
        "legal_operations",
        "marketing_operations",
        "sales_operations",
        "technology_operations",
        "finance_operations",
        "organizational_learning",
        "executive_brief",
        "organization_chart",
    }


def test_effective_feature_flags_prefers_workspace_override():
    workspace_id = generate_snowflake_id()
    global_flag = FeatureFlag(
        id=generate_snowflake_id(), workspace_id=None, key="finance_function_v13", enabled=False
    )
    workspace_flag = FeatureFlag(
        id=generate_snowflake_id(), workspace_id=workspace_id, key="finance_operations", enabled=True
    )

    assert effective_feature_flags([global_flag, workspace_flag], workspace_id) == {
        "finance_operations": True
    }


def test_feature_flags_endpoint_returns_effective_workspace_values(client):
    workspace_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=workspace_id, user_id=generate_snowflake_id(), role="admin")
    global_flag = FeatureFlag(id=generate_snowflake_id(), workspace_id=None, key="finance_function_v13", enabled=False)
    workspace_flag = FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key="finance_operations", enabled=True)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [global_flag, workspace_flag]
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(f"/api/v1/platform/feature-flags?workspace_id={workspace_id}")

    assert response.status_code == 200
    assert response.json() == {"flags": {"finance_operations": True}}


def test_legacy_key_is_normalized_and_canonical_row_wins():
    assert canonical_flag_key("sales_crm_core_v13_2") == "sales_crm"
    assert canonical_flag_key("unrelated") == "unrelated"

    workspace_id = generate_snowflake_id()
    flags = [
        FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key="sales_crm_core_v13_2", enabled=False),
        FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key="sales_crm", enabled=True),
    ]
    assert effective_feature_flags(flags, workspace_id) == {"sales_crm": True}


def test_is_enabled_reads_legacy_row_when_canonical_row_is_absent():
    db = MagicMock()
    absent = MagicMock()
    absent.first.return_value = None
    legacy = MagicMock()
    legacy.first.return_value = FeatureFlag(
        id=generate_snowflake_id(), workspace_id=None, key="sales_crm_core_v13_2", enabled=True
    )
    db.query.return_value.filter.side_effect = [absent, legacy]

    assert is_enabled(db, "sales_crm") is True


# --- Flag khoá tool AI -----------------------------------------------------
# is_enabled() trả False khi không có row, nên một flag khai báo mà chưa ai seed sẽ âm
# thầm gỡ tool tương ứng khỏi cả voice lẫn chat. Hai test dưới chặn đúng kiểu hỏng đó.


def test_every_tool_flag_is_declared_in_tool_flag_defaults():
    from app.core.feature_flags import TOOL_FLAG_DEFAULTS
    from app.core.tool_bootstrap import load_all_tools
    from app.core.tool_registry import get_registered_tools

    load_all_tools()
    used = {
        spec.flag_key
        for spec in get_registered_tools().values()
        if spec.flag_key and getattr(spec.callable, "__module__", "").startswith("app.")
    }

    missing = sorted(used - set(TOOL_FLAG_DEFAULTS))
    assert not missing, (
        f"Tool đang dùng flag {missing} nhưng flag đó không có trong TOOL_FLAG_DEFAULTS - "
        f"tool sẽ biến mất khỏi voice/chat mà không báo lỗi"
    )


def test_every_tool_flag_default_is_actually_seeded_by_a_migration():
    """Khai báo mặc định trong Python không tự tạo row trong DB. Không có bước seed thì
    mặc định đó chỉ là ý định, còn is_enabled() vẫn trả False.

    Chấp nhận cả tên cũ lẫn tên chuẩn: migration seed bằng tên nào cũng được, vì
    is_enabled() tra qua LEGACY_FLAG_ALIASES nên row tên cũ vẫn khớp flag đã đổi tên.
    Chỉ khi KHÔNG có tên nào xuất hiện trong migration thì flag mới thực sự chưa được seed.
    """
    from pathlib import Path

    from app.core.feature_flags import LEGACY_FLAG_ALIASES, TOOL_FLAG_DEFAULTS

    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    seeded_text = "\n".join(p.read_text() for p in versions.glob("*.py"))

    def _seeded(canonical: str) -> bool:
        names = {canonical} | {
            alias for alias, target in LEGACY_FLAG_ALIASES.items() if target == canonical
        }
        return any(f'"{name}"' in seeded_text for name in names)

    unseeded = sorted(key for key in TOOL_FLAG_DEFAULTS if not _seeded(key))
    assert not unseeded, (
        f"Flag {unseeded} chưa được seed trong migration nào - thêm vào một migration, "
        f"nếu không tool khoá bởi nó sẽ tắt trên mọi môi trường"
    )
