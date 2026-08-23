import pytest

from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.supply_chain.lifecycle import InvalidSkillLifecycleTransition, validate_transition


def test_discovered_to_imported_is_valid():
    validate_transition(SkillLifecycleStatus.DISCOVERED, SkillLifecycleStatus.IMPORTED)


def test_scanned_to_verified_is_valid():
    validate_transition(SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.VERIFIED)


def test_scanned_to_quarantined_is_valid():
    validate_transition(SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.QUARANTINED)


def test_discovered_to_active_is_invalid_skips_stages():
    with pytest.raises(InvalidSkillLifecycleTransition):
        validate_transition(SkillLifecycleStatus.DISCOVERED, SkillLifecycleStatus.ACTIVE)


def test_active_to_quarantined_is_valid_can_be_pulled_after_activation():
    validate_transition(SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.QUARANTINED)


def test_rejected_is_terminal():
    with pytest.raises(InvalidSkillLifecycleTransition):
        validate_transition(SkillLifecycleStatus.REJECTED, SkillLifecycleStatus.IMPORTED)
