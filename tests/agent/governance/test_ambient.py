"""Direct unit tests for ambient governance verification."""

from __future__ import annotations

import pytest

from agent.governance.ambient import verify_ambient_governance


class TestVerifyAmbientGovernance:
    """Direct tests for verify_ambient_governance function."""

    def test_none_context_allows(self) -> None:
        """None context -> allow (no constraints present)."""
        is_allowed, reason = verify_ambient_governance(None)
        assert is_allowed is True
        assert reason == ""

    def test_empty_dict_context_allows(self) -> None:
        """Empty dict context -> allow (no constraints present)."""
        is_allowed, reason = verify_ambient_governance({})
        assert is_allowed is True
        assert reason == ""

    def test_active_tenant_active_principal_allows(self) -> None:
        """Default tenant_status and principal_status (both active) -> allow."""
        context = {
            "tenant_status": "active",
            "principal_status": "active",
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is True
        assert reason == ""

    def test_defaults_to_active_when_missing(self) -> None:
        """When tenant_status/principal_status missing, defaults to 'active' -> allow."""
        is_allowed, reason = verify_ambient_governance({})
        assert is_allowed is True
        assert reason == ""

    def test_tenant_status_suspended_denies(self) -> None:
        """tenant_status='suspended' -> deny."""
        context = {"tenant_status": "suspended"}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Tenant is currently suspended" == reason

    def test_tenant_status_disabled_denies(self) -> None:
        """tenant_status='disabled' -> deny."""
        context = {"tenant_status": "disabled"}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Tenant is currently disabled" == reason

    def test_principal_status_revoked_denies(self) -> None:
        """principal_status='revoked' -> deny."""
        context = {"principal_status": "revoked"}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Principal is currently revoked" == reason

    def test_principal_status_disabled_denies(self) -> None:
        """principal_status='disabled' -> deny."""
        context = {"principal_status": "disabled"}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Principal is currently disabled" == reason

    def test_emergency_lock_true_denies(self) -> None:
        """emergency_lock=True -> deny with kill switch message."""
        context = {"emergency_lock": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Emergency lock / kill switch is active" == reason

    def test_kill_switch_true_denies(self) -> None:
        """kill_switch=True -> deny with kill switch message."""
        context = {"kill_switch": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Emergency lock / kill switch is active" == reason

    def test_both_emergency_lock_and_kill_switch_denies(self) -> None:
        """Both emergency_lock and kill_switch true -> deny."""
        context = {"emergency_lock": True, "kill_switch": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Emergency lock / kill switch is active" == reason

    def test_human_takeover_true_denies(self) -> None:
        """human_takeover=True -> deny with takeover message."""
        context = {"human_takeover": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Human takeover is active" == reason

    def test_takeover_true_denies(self) -> None:
        """takeover=True -> deny with takeover message."""
        context = {"takeover": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Human takeover is active" == reason

    def test_thread_takeover_true_denies(self) -> None:
        """thread_takeover=True -> deny with takeover message."""
        context = {"thread_takeover": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Human takeover is active" == reason

    def test_all_three_takeover_variants_deny(self) -> None:
        """Any of human_takeover/takeover/thread_takeover=True denies."""
        # human_takeover only
        context1 = {"human_takeover": True, "takeover": False, "thread_takeover": False}
        is_allowed1, _ = verify_ambient_governance(context1)
        assert is_allowed1 is False

        # takeover only
        context2 = {"human_takeover": False, "takeover": True, "thread_takeover": False}
        is_allowed2, _ = verify_ambient_governance(context2)
        assert is_allowed2 is False

        # thread_takeover only
        context3 = {"human_takeover": False, "takeover": False, "thread_takeover": True}
        is_allowed3, _ = verify_ambient_governance(context3)
        assert is_allowed3 is False

    def test_context_with_metadata_dict(self) -> None:
        """Context object with .metadata dict extracts from it."""
        # Mock object with metadata attribute
        class ContextWithMetadata:
            def __init__(self, metadata: dict) -> None:
                self.metadata = metadata

        context = ContextWithMetadata({"tenant_status": "suspended"})
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Tenant is currently suspended" == reason

    def test_context_with_policy_snapshot_merges(self) -> None:
        """Context with metadata and policy_snapshot merges both."""
        # Mock object with metadata and policy_snapshot
        class ContextWithBoth:
            def __init__(self, metadata: dict, policy_snapshot: dict) -> None:
                self.metadata = metadata
                self.policy_snapshot = policy_snapshot

        context = ContextWithBoth(
            {"tenant_status": "active"},
            {"principal_status": "revoked"},
        )
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Principal is currently revoked" == reason

    def test_policy_snapshot_wins_over_metadata(self) -> None:
        """When same key in both metadata and policy_snapshot, policy_snapshot wins."""
        class ContextWithBoth:
            def __init__(self, metadata: dict, policy_snapshot: dict) -> None:
                self.metadata = metadata
                self.policy_snapshot = policy_snapshot

        context = ContextWithBoth(
            {"tenant_status": "active"},
            {"tenant_status": "suspended"},  # Overrides metadata
        )
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Tenant is currently suspended" == reason

    def test_context_without_metadata_attribute_treats_as_dict(self) -> None:
        """Context object without .metadata attr is treated as dict."""
        context = {"emergency_lock": True}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False

    def test_priority_tenant_status_checked_first(self) -> None:
        """tenant_status suspended takes precedence (checked in priority order)."""
        context = {
            "tenant_status": "suspended",
            "principal_status": "revoked",
            "emergency_lock": True,
            "human_takeover": True,
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        # First deny condition wins
        assert "Tenant is currently suspended" == reason

    def test_principal_checked_before_emergency_lock(self) -> None:
        """principal_status checked before emergency_lock."""
        context = {
            "principal_status": "disabled",
            "emergency_lock": True,
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Principal is currently disabled" == reason

    def test_emergency_lock_checked_before_takeover(self) -> None:
        """emergency_lock/kill_switch checked before takeover flags."""
        context = {
            "emergency_lock": True,
            "human_takeover": True,
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Emergency lock / kill switch is active" == reason

    def test_all_flags_false_allows(self) -> None:
        """All control flags false/not present -> allow."""
        context = {
            "tenant_status": "active",
            "principal_status": "active",
            "emergency_lock": False,
            "kill_switch": False,
            "human_takeover": False,
            "takeover": False,
            "thread_takeover": False,
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is True
        assert reason == ""

    def test_extra_fields_in_context_ignored(self) -> None:
        """Extra fields in context dict don't affect checks."""
        context = {
            "tenant_status": "active",
            "extra_field_1": "value",
            "extra_field_2": 123,
            "another_field": True,
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is True
        assert reason == ""

    def test_metadata_dict_is_not_instance_check(self) -> None:
        """Non-dict metadata (e.g. string) is handled gracefully."""
        class ContextWithNonDictMetadata:
            def __init__(self) -> None:
                self.metadata = "not a dict"

        context = ContextWithNonDictMetadata()
        # Should treat as empty dict (metadata is not a dict)
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is True
        assert reason == ""

    def test_falsy_policy_snapshot_ignored(self) -> None:
        """Falsy policy_snapshot (None, empty dict, etc) is ignored."""
        class ContextWithFalsySnapshot:
            def __init__(self) -> None:
                self.metadata = {"tenant_status": "suspended"}
                self.policy_snapshot = None

        context = ContextWithFalsySnapshot()
        # metadata's suspended status should still deny
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        assert "Tenant is currently suspended" == reason

    def test_unknown_tenant_status_value_allows(self) -> None:
        """Unknown tenant_status value (not 'suspended' or 'disabled') allows."""
        context = {"tenant_status": "unknown_status"}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is True

    def test_unknown_principal_status_value_allows(self) -> None:
        """Unknown principal_status value (not 'revoked' or 'disabled') allows."""
        context = {"principal_status": "unknown_status"}
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is True

    def test_all_negative_denials_combined(self) -> None:
        """Multiple deny conditions — first one wins."""
        context = {
            "tenant_status": "suspended",
            "principal_status": "revoked",
        }
        is_allowed, reason = verify_ambient_governance(context)
        assert is_allowed is False
        # Tenant checked first
        assert "tenant" in reason.lower()
