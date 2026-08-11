import uuid
from unittest.mock import MagicMock
import pytest

from app.modules.platform.models import FeatureFlag
from app.core.feature_flags import (
    is_enabled,
    set_feature_flag,
    list_feature_flags,
    FLAG_PROJECT_CLASSIFIER_V12,
    FLAG_CYCLE_13WEEK_V12,
    FLAG_MILESTONES_GATES_V12,
)


def test_is_enabled_default_false_when_no_flag():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    assert is_enabled(db, "unknown_flag") is False
    assert is_enabled(db, FLAG_PROJECT_CLASSIFIER_V12, workspace_id=uuid.uuid4()) is False


def test_is_enabled_global_flag():
    db = MagicMock()
    global_flag = FeatureFlag(
        id=uuid.uuid4(),
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
    ws_id = uuid.uuid4()
    ws_flag = FeatureFlag(
        id=uuid.uuid4(),
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
        id=uuid.uuid4(),
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

