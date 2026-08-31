"""Tests for apps/cosa/compliance/statutory_floor module.

Coverage audit Task B: Giải quyết gap zero-coverage của StatutoryFloor
và FloorDecision. File test_statutory_floor.py cũ chỉ test CosaPolicyEngine
chứ không test statutory_floor.py — file này cung cấp coverage thực.
"""

from __future__ import annotations

import pytest

from apps.cosa.compliance.contracts import ComplianceSnapshot
from apps.cosa.compliance.statutory_floor import FloorDecision, StatutoryFloor


class TestFloorDecision:
    """FloorDecision dataclass tests."""

    def test_deny_factory_method(self) -> None:
        """FloorDecision.deny() tạo DENY decision với một reason."""
        decision = FloorDecision.deny("TEST_REASON")
        assert decision.action == "DENY"
        assert decision.reasons == ("TEST_REASON",)
        assert decision.is_deny is True

    def test_continue_factory_method(self) -> None:
        """FloorDecision.continue_() tạo CONTINUE decision."""
        decision = FloorDecision.continue_()
        assert decision.action == "CONTINUE"
        assert decision.reasons == ()
        assert decision.is_deny is False

    def test_direct_construction_deny(self) -> None:
        """Xây dựng FloorDecision DENY trực tiếp."""
        decision = FloorDecision(action="DENY", reasons=("Reason1", "Reason2"))
        assert decision.action == "DENY"
        assert decision.reasons == ("Reason1", "Reason2")
        assert decision.is_deny is True

    def test_direct_construction_continue(self) -> None:
        """Xây dựng FloorDecision CONTINUE trực tiếp."""
        decision = FloorDecision(action="CONTINUE", reasons=())
        assert decision.action == "CONTINUE"
        assert decision.reasons == ()
        assert decision.is_deny is False

    def test_is_deny_property(self) -> None:
        """is_deny property phản ánh action."""
        deny_decision = FloorDecision.deny("reason")
        continue_decision = FloorDecision.continue_()

        assert deny_decision.is_deny is True
        assert continue_decision.is_deny is False

    def test_dataclass_frozen(self) -> None:
        """FloorDecision là frozen (immutable)."""
        decision = FloorDecision.deny("reason")
        with pytest.raises(Exception):  # FrozenInstanceError từ dataclass(frozen=True)
            decision.action = "CONTINUE"


class TestStatutoryFloor:
    """StatutoryFloor evaluate() logic tests."""

    def test_missing_snapshot_denies(self) -> None:
        """Snapshot None → DENY với COMPLIANCE_SNAPSHOT_MISSING."""
        floor = StatutoryFloor()
        decision = floor.evaluate("any.capability", {}, snapshot=None)

        assert decision.is_deny
        assert decision.reasons == ("COMPLIANCE_SNAPSHOT_MISSING",)

    def test_prohibited_purpose_denies(self) -> None:
        """prohibited_purpose=True → DENY với PROHIBITED_DECISION_DOMAIN."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["capability.id"],
            "prohibited_purpose": True,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("normal.capability", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)

    def test_hr_capability_denies(self) -> None:
        """capability_id.startswith('hr.') → DENY với PROHIBITED_DECISION_DOMAIN."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["hr.candidate.rank"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("hr.candidate.rank", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)

    def test_candidate_rank_in_capability_denies(self) -> None:
        """'candidate.rank' in capability_id → DENY với PROHIBITED_DECISION_DOMAIN."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["some.candidate.rank.capability"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("some.candidate.rank.capability", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)

    def test_credit_score_in_capability_denies(self) -> None:
        """'credit.score' in capability_id → DENY với PROHIBITED_DECISION_DOMAIN."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["risk.credit.score.check"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("risk.credit.score.check", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)

    def test_non_approved_status_denies(self) -> None:
        """status != 'APPROVED_FOR_USE' → DENY với DEPLOYMENT_NOT_APPROVED."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "PENDING_REVIEW",
            "allowed_capabilities": ["capability.id"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("capability.id", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("DEPLOYMENT_NOT_APPROVED",)

    def test_non_advisory_mode_denies(self) -> None:
        """mode != 'ADVISORY_ONLY' → DENY với NON_ADVISORY_MODE."""
        snapshot = {
            "mode": "PREDICTIVE",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["capability.id"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("capability.id", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("NON_ADVISORY_MODE",)

    def test_wildcard_allows_all_capabilities(self) -> None:
        """'*' trong allowed_capabilities → CONTINUE."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["*"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("any.random.capability", {}, snapshot=snapshot)

        assert decision.action == "CONTINUE"
        assert decision.reasons == ()

    def test_unbound_capability_denies(self) -> None:
        """capability_id không trong allowed_set → DENY với CAPABILITY_NOT_BOUND."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["finance.read", "finance.write"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("hr.candidate.rank", {}, snapshot=snapshot)

        # Nhưng 'hr.' prefix sẽ catch trước, vì vậy lỗi này không xảy ra
        # Hãy test một capability khác không match bất kỳ quy tắc nào
        decision = floor.evaluate("marketing.campaign", {}, snapshot=snapshot)
        assert decision.is_deny
        assert decision.reasons == ("CAPABILITY_NOT_BOUND",)

    def test_approved_allowed_capability_continues(self) -> None:
        """Capability được phép, mode ADVISORY_ONLY, status APPROVED → CONTINUE."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["finance.read", "finance.write"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("finance.read", {}, snapshot=snapshot)

        assert decision.action == "CONTINUE"
        assert decision.reasons == ()

    def test_snapshot_as_dict(self) -> None:
        """Hỗ trợ snapshot dưới dạng dict."""
        snapshot_dict = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["capability.id"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("capability.id", {}, snapshot=snapshot_dict)

        assert decision.action == "CONTINUE"

    def test_snapshot_as_pydantic_model(self) -> None:
        """Hỗ trợ snapshot dưới dạng ComplianceSnapshot (Pydantic model)."""
        from datetime import datetime, timezone

        snapshot_model = ComplianceSnapshot(
            workspace_id="ws_1",
            deployment_id="dep_1",
            assessment_id="ass_1",
            mode="ADVISORY_ONLY",
            status="APPROVED_FOR_USE",
            allowed_capabilities=frozenset(["capability.id"]),
            provider_profile_version="v1",
            data_profile_version="v1",
            provider_key="provider_1",
            model_key="model_1",
            purpose_id="purpose_1",
            retention_policy_id="retention_1",
            snapshot_hash="sha256:test",
            expires_at=datetime.now(timezone.utc),
        )
        floor = StatutoryFloor()
        decision = floor.evaluate("capability.id", {}, snapshot=snapshot_model)

        assert decision.action == "CONTINUE"

    def test_snapshot_without_allowed_capabilities(self) -> None:
        """Xử lý snapshot không có allowed_capabilities (None)."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": None,
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("any.capability", {}, snapshot=snapshot)

        # None → set() → capability không trong set → DENY
        assert decision.is_deny
        assert decision.reasons == ("CAPABILITY_NOT_BOUND",)

    def test_empty_allowed_capabilities(self) -> None:
        """Xử lý empty allowed_capabilities."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": [],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("any.capability", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("CAPABILITY_NOT_BOUND",)

    def test_multiple_disqualifying_conditions_first_wins(self) -> None:
        """Khi có nhiều điều kiện từ chối, lý do đầu tiên được trả về."""
        # prohibited_purpose + non-approved status
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "PENDING",
            "allowed_capabilities": ["capability.id"],
            "prohibited_purpose": True,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("capability.id", {}, snapshot=snapshot)

        # prohibited_purpose được kiểm tra trước
        assert decision.is_deny
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)

    def test_evaluate_ignores_payload(self) -> None:
        """evaluate() không sử dụng payload parameter."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["capability.id"],
            "prohibited_purpose": False,
        }
        floor = StatutoryFloor()

        # payload khác nhau không ảnh hưởng đến kết quả
        decision1 = floor.evaluate("capability.id", {}, snapshot=snapshot)
        decision2 = floor.evaluate("capability.id", {"key": "value"}, snapshot=snapshot)
        decision3 = floor.evaluate("capability.id", {"nested": {"data": "here"}}, snapshot=snapshot)

        assert decision1.action == decision2.action == decision3.action == "CONTINUE"

    def test_pydantic_model_missing_optional_fields(self) -> None:
        """Xử lý ComplianceSnapshot khi getattr trả về None cho optional fields."""
        from datetime import datetime, timezone

        # ComplianceSnapshot có một số field không bắt buộc, test xử lý nhất quán
        snapshot = ComplianceSnapshot(
            workspace_id="ws_1",
            deployment_id="dep_1",
            assessment_id="ass_1",
            mode="ADVISORY_ONLY",
            status="APPROVED_FOR_USE",
            allowed_capabilities=frozenset(),  # empty
            provider_profile_version="v1",
            data_profile_version="v1",
            provider_key="provider_1",
            model_key="model_1",
            purpose_id="purpose_1",
            retention_policy_id="retention_1",
            snapshot_hash="sha256:test",
            expires_at=datetime.now(timezone.utc),
        )
        floor = StatutoryFloor()
        decision = floor.evaluate("any.capability", {}, snapshot=snapshot)

        assert decision.is_deny
        assert decision.reasons == ("CAPABILITY_NOT_BOUND",)

    def test_decision_order_checks_prohibited_before_others(self) -> None:
        """Hệ thống kiểm tra prohibited trước các điều kiện khác."""
        snapshot = {
            "mode": "ADVISORY_ONLY",
            "status": "APPROVED_FOR_USE",
            "allowed_capabilities": ["hr.candidate.rank"],
            "prohibited_purpose": True,
        }
        floor = StatutoryFloor()
        decision = floor.evaluate("hr.candidate.rank", {}, snapshot=snapshot)

        # prohibited_purpose được kiểm tra trước HR prefix
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)
