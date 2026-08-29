from __future__ import annotations

from agent.contracts.capability import (
    CapabilityImplementationIdentity,
    CapabilitySpec,
)
from agent.governance.contracts import CapabilityRisk


def test_l3_capability_implementation_identity():
    """Kiểm thử L3 Capability Implementation Identity (ADR-A)."""
    identity1 = CapabilityImplementationIdentity(
        capability_id="finance.payout.execute",
        handler_version="1.2.0",
        schema_version="1.0.0",
        connector_implementation_hash="hash_connector_v1",
    )
    hash1 = identity1.compute_identity_hash()

    identity2 = CapabilityImplementationIdentity(
        capability_id="finance.payout.execute",
        handler_version="1.3.0",  # Changed version
        schema_version="1.0.0",
        connector_implementation_hash="hash_connector_v1",
    )
    hash2 = identity2.compute_identity_hash()

    assert hash1 != hash2

    spec = CapabilitySpec(
        id="finance.payout.execute",
        risk=CapabilityRisk.HIGH,
        implementation_identity=identity1,
    )
    assert spec.implementation_identity is not None
    assert spec.implementation_identity.handler_version == "1.2.0"
