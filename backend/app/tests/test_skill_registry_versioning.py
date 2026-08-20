"""G1 §61-62 / G3 Phase 1C: Skill Registry Versioning - EXPERIMENTAL/ARCHIVED/BLOCKED
lifecycle states, the platform-immutable (`is_system`) vs. workspace-authored
distinction, and the fix for the auto-seed-on-first-view bug that used to
attribute a fabricated approval to whoever happened to view the list first.
"""
from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.workforce.skills.models import SkillRegistryItem
from app.workforce.skills.service import SkillLifecycleService


def _mock_db_with_item(item: SkillRegistryItem) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = item
    return db


def test_seed_platform_skill_is_active_and_system_owned_without_a_fake_approver():
    db = MagicMock()
    item = SkillLifecycleService.seed_platform_skill(
        db=db,
        workspace_id=1,
        name="sales.lead_qualification",
        domain="sales",
        instructions="1. Score the lead. 2. Route to the right rep.",
        description="Built-in SOP",
    )
    assert item.status == "active"
    assert item.is_system is True
    assert item.approved_by_user_id is None
    assert item.approved_at is None


def test_seed_platform_skill_still_runs_the_safety_scanner():
    db = MagicMock()
    with pytest.raises(ValueError, match="rejected by Safety Scanner"):
        SkillLifecycleService.seed_platform_skill(
            db=db,
            workspace_id=1,
            name="leaky.built_in",
            domain="tech",
            instructions="Use key sk-abcdef12345678901234567890123456 to authenticate.",
        )


def test_promote_skill_defaults_to_active():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(id=skill_id, workspace_id=1, name="x", domain="sales", status="pending_approval")
    db = _mock_db_with_item(item)

    promoted = SkillLifecycleService.promote_skill(db, skill_id, approved_by_user_id=10)
    assert promoted.status == "active"
    assert promoted.approved_by_user_id == 10


def test_promote_skill_can_target_experimental():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(id=skill_id, workspace_id=1, name="x", domain="sales", status="pending_approval")
    db = _mock_db_with_item(item)

    promoted = SkillLifecycleService.promote_skill(db, skill_id, approved_by_user_id=10, target_status="experimental")
    assert promoted.status == "experimental"
    assert promoted.approved_by_user_id == 10  # still a real human approval, just flagged unstable


def test_promote_skill_rejects_an_invalid_target_status():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(id=skill_id, workspace_id=1, name="x", domain="sales", status="pending_approval")
    db = _mock_db_with_item(item)

    with pytest.raises(ValueError, match="Invalid promotion target_status"):
        SkillLifecycleService.promote_skill(db, skill_id, approved_by_user_id=10, target_status="deprecated")


def test_archive_skill_sets_terminal_status_and_optional_reason():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(id=skill_id, workspace_id=1, name="x", domain="sales", status="deprecated")
    db = _mock_db_with_item(item)

    archived = SkillLifecycleService.archive_skill(db, skill_id, user_id=1, reason="Superseded by v2")
    assert archived.status == "archived"
    assert archived.rejection_reason == "Superseded by v2"


def test_block_skill_requires_a_reason():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(id=skill_id, workspace_id=1, name="x", domain="sales", status="active")
    db = _mock_db_with_item(item)

    with pytest.raises(ValueError, match="requires a non-empty reason"):
        SkillLifecycleService.block_skill(db, skill_id, user_id=1, reason="   ")


def test_block_skill_disables_regardless_of_prior_status():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(id=skill_id, workspace_id=1, name="x", domain="sales", status="active")
    db = _mock_db_with_item(item)

    blocked = SkillLifecycleService.block_skill(db, skill_id, user_id=1, reason="Failed security review")
    assert blocked.status == "blocked"
    assert blocked.rejection_reason == "Failed security review"


def test_update_skill_refuses_to_edit_a_system_skill():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(
        id=skill_id, workspace_id=1, name="sales.lead_qualification", domain="sales",
        instructions="Built-in SOP", is_system=True,
    )
    db = _mock_db_with_item(item)

    with pytest.raises(PermissionError, match="immutable"):
        SkillLifecycleService.update_skill(db, skill_id, description="trying to edit the built-in")


def test_update_skill_still_allows_editing_workspace_authored_skills():
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(
        id=skill_id, workspace_id=1, name="custom.skill", domain="sales",
        instructions="My own SOP", is_system=False,
    )
    db = _mock_db_with_item(item)

    updated = SkillLifecycleService.update_skill(db, skill_id, description="new description")
    assert updated.description == "new description"
