"""Direct unit tests for workforce persistence models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from agent.workforce.models import (
    RunCostObservationRecord,
    RuntimeSignalOutboxRecord,
    WorkforceAssignmentRecord,
)


class TestWorkforceAssignmentRecord:
    """Direct construction tests for WorkforceAssignmentRecord dataclass."""

    def test_create_with_required_fields_only(self) -> None:
        """Construct with all required fields, retired_at defaults to None."""
        now = datetime.now(UTC)
        assignment_id = uuid4()

        record = WorkforceAssignmentRecord(
            assignment_id=assignment_id,
            workspace_id="ws_001",
            functional_key="campaign_planner",
            spec_id="spec.campaign_planner",
            spec_version="1.0.0",
            definition_hash="sha256:abc123",
            reports_to_assignment_id=None,
            configured_by="user:admin",
            status="ACTIVE",
            created_at=now,
        )

        assert record.assignment_id == assignment_id
        assert record.workspace_id == "ws_001"
        assert record.functional_key == "campaign_planner"
        assert record.spec_id == "spec.campaign_planner"
        assert record.spec_version == "1.0.0"
        assert record.definition_hash == "sha256:abc123"
        assert record.reports_to_assignment_id is None
        assert record.configured_by == "user:admin"
        assert record.status == "ACTIVE"
        assert record.created_at == now
        assert record.retired_at is None

    def test_create_with_all_fields_including_retired_at(self) -> None:
        """Construct with all fields including optional retired_at."""
        now = datetime.now(UTC)
        retired_now = datetime.now(UTC)
        assignment_id = uuid4()
        parent_id = uuid4()

        record = WorkforceAssignmentRecord(
            assignment_id=assignment_id,
            workspace_id="ws_002",
            functional_key="compliance_analyst",
            spec_id="spec.compliance",
            spec_version="2.0.0",
            definition_hash="sha256:def456",
            reports_to_assignment_id=parent_id,
            configured_by="user:manager",
            status="RETIRED",
            created_at=now,
            retired_at=retired_now,
        )

        assert record.status == "RETIRED"
        assert record.retired_at == retired_now
        assert record.reports_to_assignment_id == parent_id

    def test_frozen_prevents_mutation(self) -> None:
        """Frozen dataclass prevents attribute assignment after construction."""
        now = datetime.now(UTC)
        record = WorkforceAssignmentRecord(
            assignment_id=uuid4(),
            workspace_id="ws_003",
            functional_key="test_role",
            spec_id="spec.test",
            spec_version="1.0.0",
            definition_hash="sha256:xyz",
            reports_to_assignment_id=None,
            configured_by="user:test",
            status="ACTIVE",
            created_at=now,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            record.status = "RETIRED"  # type: ignore

    def test_literal_status_accepts_active_and_retired(self) -> None:
        """Status field accepts only ACTIVE or RETIRED literals."""
        now = datetime.now(UTC)

        # ACTIVE is accepted
        active = WorkforceAssignmentRecord(
            assignment_id=uuid4(),
            workspace_id="ws_004",
            functional_key="role1",
            spec_id="spec1",
            spec_version="1.0.0",
            definition_hash="hash",
            reports_to_assignment_id=None,
            configured_by="user",
            status="ACTIVE",
            created_at=now,
        )
        assert active.status == "ACTIVE"

        # RETIRED is accepted
        retired = WorkforceAssignmentRecord(
            assignment_id=uuid4(),
            workspace_id="ws_004",
            functional_key="role1",
            spec_id="spec1",
            spec_version="1.0.0",
            definition_hash="hash",
            reports_to_assignment_id=None,
            configured_by="user",
            status="RETIRED",
            created_at=now,
        )
        assert retired.status == "RETIRED"

    def test_equality_comparison(self) -> None:
        """Dataclass equality based on all field values."""
        now = datetime.now(UTC)
        assignment_id = uuid4()

        record1 = WorkforceAssignmentRecord(
            assignment_id=assignment_id,
            workspace_id="ws_005",
            functional_key="role",
            spec_id="spec",
            spec_version="1.0.0",
            definition_hash="hash",
            reports_to_assignment_id=None,
            configured_by="user",
            status="ACTIVE",
            created_at=now,
        )

        record2 = WorkforceAssignmentRecord(
            assignment_id=assignment_id,
            workspace_id="ws_005",
            functional_key="role",
            spec_id="spec",
            spec_version="1.0.0",
            definition_hash="hash",
            reports_to_assignment_id=None,
            configured_by="user",
            status="ACTIVE",
            created_at=now,
        )

        assert record1 == record2

    def test_inequality_on_different_field(self) -> None:
        """Inequality when any field differs."""
        now = datetime.now(UTC)
        assignment_id = uuid4()

        record1 = WorkforceAssignmentRecord(
            assignment_id=assignment_id,
            workspace_id="ws_006",
            functional_key="role",
            spec_id="spec",
            spec_version="1.0.0",
            definition_hash="hash",
            reports_to_assignment_id=None,
            configured_by="user",
            status="ACTIVE",
            created_at=now,
        )

        record2 = WorkforceAssignmentRecord(
            assignment_id=uuid4(),  # Different ID
            workspace_id="ws_006",
            functional_key="role",
            spec_id="spec",
            spec_version="1.0.0",
            definition_hash="hash",
            reports_to_assignment_id=None,
            configured_by="user",
            status="ACTIVE",
            created_at=now,
        )

        assert record1 != record2


class TestRuntimeSignalOutboxRecord:
    """Direct construction tests for RuntimeSignalOutboxRecord dataclass."""

    def test_create_with_required_fields_only(self) -> None:
        """Construct with all required fields, delivered_at defaults to None."""
        now = datetime.now(UTC)
        next_attempt = datetime.now(UTC)
        outbox_id = uuid4()

        record = RuntimeSignalOutboxRecord(
            outbox_id=outbox_id,
            workspace_id="ws_001",
            source_kind="agent_run",
            source_id="run_abc123",
            sequence=1,
            state="PENDING",
            observed_at=now,
            correlation_id="corr_xyz",
            payload_hash="hash_payload",
            state_delivery="PENDING",
            attempt_count=0,
            next_attempt_at=next_attempt,
        )

        assert record.outbox_id == outbox_id
        assert record.workspace_id == "ws_001"
        assert record.source_kind == "agent_run"
        assert record.source_id == "run_abc123"
        assert record.sequence == 1
        assert record.state == "PENDING"
        assert record.observed_at == now
        assert record.correlation_id == "corr_xyz"
        assert record.payload_hash == "hash_payload"
        assert record.state_delivery == "PENDING"
        assert record.attempt_count == 0
        assert record.next_attempt_at == next_attempt
        assert record.delivered_at is None

    def test_create_with_delivered_at(self) -> None:
        """Construct with optional delivered_at field set."""
        now = datetime.now(UTC)
        next_attempt = datetime.now(UTC)
        delivered = datetime.now(UTC)
        outbox_id = uuid4()

        record = RuntimeSignalOutboxRecord(
            outbox_id=outbox_id,
            workspace_id="ws_002",
            source_kind="agent_run",
            source_id="run_def456",
            sequence=2,
            state="SUCCEEDED",
            observed_at=now,
            correlation_id="corr_abc",
            payload_hash="hash_delivered",
            state_delivery="DELIVERED",
            attempt_count=1,
            next_attempt_at=next_attempt,
            delivered_at=delivered,
        )

        assert record.state_delivery == "DELIVERED"
        assert record.delivered_at == delivered

    def test_literal_state_delivery_values(self) -> None:
        """state_delivery accepts only PENDING, DELIVERED, or FAILED."""
        now = datetime.now(UTC)
        next_attempt = datetime.now(UTC)

        # PENDING
        pending = RuntimeSignalOutboxRecord(
            outbox_id=uuid4(),
            workspace_id="ws",
            source_kind="agent_run",
            source_id="run_1",
            sequence=1,
            state="STATE",
            observed_at=now,
            correlation_id="corr",
            payload_hash="hash",
            state_delivery="PENDING",
            attempt_count=0,
            next_attempt_at=next_attempt,
        )
        assert pending.state_delivery == "PENDING"

        # DELIVERED
        delivered = RuntimeSignalOutboxRecord(
            outbox_id=uuid4(),
            workspace_id="ws",
            source_kind="agent_run",
            source_id="run_2",
            sequence=2,
            state="STATE",
            observed_at=now,
            correlation_id="corr",
            payload_hash="hash",
            state_delivery="DELIVERED",
            attempt_count=1,
            next_attempt_at=next_attempt,
        )
        assert delivered.state_delivery == "DELIVERED"

        # FAILED
        failed = RuntimeSignalOutboxRecord(
            outbox_id=uuid4(),
            workspace_id="ws",
            source_kind="agent_run",
            source_id="run_3",
            sequence=3,
            state="STATE",
            observed_at=now,
            correlation_id="corr",
            payload_hash="hash",
            state_delivery="FAILED",
            attempt_count=2,
            next_attempt_at=next_attempt,
        )
        assert failed.state_delivery == "FAILED"

    def test_frozen_prevents_mutation(self) -> None:
        """Frozen dataclass prevents attribute assignment."""
        now = datetime.now(UTC)
        next_attempt = datetime.now(UTC)
        record = RuntimeSignalOutboxRecord(
            outbox_id=uuid4(),
            workspace_id="ws",
            source_kind="agent_run",
            source_id="run",
            sequence=1,
            state="STATE",
            observed_at=now,
            correlation_id="corr",
            payload_hash="hash",
            state_delivery="PENDING",
            attempt_count=0,
            next_attempt_at=next_attempt,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            record.attempt_count = 5  # type: ignore

    def test_equality_based_on_all_fields(self) -> None:
        """Equality comparison includes all fields."""
        now = datetime.now(UTC)
        next_attempt = datetime.now(UTC)
        outbox_id = uuid4()

        record1 = RuntimeSignalOutboxRecord(
            outbox_id=outbox_id,
            workspace_id="ws_003",
            source_kind="agent_run",
            source_id="run_equal",
            sequence=1,
            state="STATE",
            observed_at=now,
            correlation_id="corr_eq",
            payload_hash="hash_eq",
            state_delivery="PENDING",
            attempt_count=0,
            next_attempt_at=next_attempt,
        )

        record2 = RuntimeSignalOutboxRecord(
            outbox_id=outbox_id,
            workspace_id="ws_003",
            source_kind="agent_run",
            source_id="run_equal",
            sequence=1,
            state="STATE",
            observed_at=now,
            correlation_id="corr_eq",
            payload_hash="hash_eq",
            state_delivery="PENDING",
            attempt_count=0,
            next_attempt_at=next_attempt,
        )

        assert record1 == record2


class TestRunCostObservationRecord:
    """Direct construction tests for RunCostObservationRecord dataclass."""

    def test_create_with_all_fields_populated(self) -> None:
        """Construct with all fields including optional numeric/string fields."""
        now = datetime.now(UTC)
        observation_id = uuid4()

        record = RunCostObservationRecord(
            observation_id=observation_id,
            workspace_id="ws_001",
            run_id="run_cost_001",
            provider_key="openai",
            model_key="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            cost_amount=Decimal("0.005"),
            currency="USD",
            observed_at=now,
        )

        assert record.observation_id == observation_id
        assert record.workspace_id == "ws_001"
        assert record.run_id == "run_cost_001"
        assert record.provider_key == "openai"
        assert record.model_key == "gpt-4o"
        assert record.input_tokens == 100
        assert record.output_tokens == 200
        assert record.cost_amount == Decimal("0.005")
        assert record.currency == "USD"
        assert record.observed_at == now

    def test_create_with_optional_fields_as_none(self) -> None:
        """Construct with optional token/cost/currency fields as None."""
        now = datetime.now(UTC)

        record = RunCostObservationRecord(
            observation_id=uuid4(),
            workspace_id="ws_002",
            run_id="run_cost_002",
            provider_key="deepseek",
            model_key="deepseek-chat",
            input_tokens=None,
            output_tokens=None,
            cost_amount=None,
            currency=None,
            observed_at=now,
        )

        assert record.input_tokens is None
        assert record.output_tokens is None
        assert record.cost_amount is None
        assert record.currency is None

    def test_cost_amount_as_float(self) -> None:
        """cost_amount can be Decimal or float."""
        now = datetime.now(UTC)

        # As float
        record_float = RunCostObservationRecord(
            observation_id=uuid4(),
            workspace_id="ws_003",
            run_id="run_float_cost",
            provider_key="provider",
            model_key="model",
            input_tokens=50,
            output_tokens=100,
            cost_amount=0.0025,
            currency="USD",
            observed_at=now,
        )

        assert isinstance(record_float.cost_amount, float)
        assert record_float.cost_amount == 0.0025

    def test_zero_tokens_are_valid(self) -> None:
        """Zero tokens are valid (0 input/output is legitimate)."""
        now = datetime.now(UTC)

        record = RunCostObservationRecord(
            observation_id=uuid4(),
            workspace_id="ws_004",
            run_id="run_zero_tokens",
            provider_key="provider",
            model_key="model",
            input_tokens=0,
            output_tokens=0,
            cost_amount=0.0,
            currency="USD",
            observed_at=now,
        )

        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.cost_amount == 0.0

    def test_frozen_prevents_mutation(self) -> None:
        """Frozen dataclass prevents attribute assignment."""
        now = datetime.now(UTC)
        record = RunCostObservationRecord(
            observation_id=uuid4(),
            workspace_id="ws_005",
            run_id="run_frozen",
            provider_key="provider",
            model_key="model",
            input_tokens=10,
            output_tokens=20,
            cost_amount=Decimal("0.001"),
            currency="USD",
            observed_at=now,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            record.input_tokens = 999  # type: ignore

    def test_equality_comparison(self) -> None:
        """Equality based on all field values."""
        now = datetime.now(UTC)
        observation_id = uuid4()

        record1 = RunCostObservationRecord(
            observation_id=observation_id,
            workspace_id="ws_006",
            run_id="run_eq",
            provider_key="provider",
            model_key="model",
            input_tokens=10,
            output_tokens=20,
            cost_amount=Decimal("0.001"),
            currency="USD",
            observed_at=now,
        )

        record2 = RunCostObservationRecord(
            observation_id=observation_id,
            workspace_id="ws_006",
            run_id="run_eq",
            provider_key="provider",
            model_key="model",
            input_tokens=10,
            output_tokens=20,
            cost_amount=Decimal("0.001"),
            currency="USD",
            observed_at=now,
        )

        assert record1 == record2

    def test_inequality_on_cost_difference(self) -> None:
        """Inequality when cost_amount differs."""
        now = datetime.now(UTC)
        observation_id = uuid4()

        record1 = RunCostObservationRecord(
            observation_id=observation_id,
            workspace_id="ws_007",
            run_id="run_diff",
            provider_key="provider",
            model_key="model",
            input_tokens=10,
            output_tokens=20,
            cost_amount=Decimal("0.001"),
            currency="USD",
            observed_at=now,
        )

        record2 = RunCostObservationRecord(
            observation_id=observation_id,
            workspace_id="ws_007",
            run_id="run_diff",
            provider_key="provider",
            model_key="model",
            input_tokens=10,
            output_tokens=20,
            cost_amount=Decimal("0.002"),  # Different cost
            currency="USD",
            observed_at=now,
        )

        assert record1 != record2
