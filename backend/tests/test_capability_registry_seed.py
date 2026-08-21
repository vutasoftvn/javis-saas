"""G1 §4 / G3 Phase 1B: seeding the canonical Capability Registry from the
two sources that used to be separate, competing CapabilityDefinition shapes.
"""
from unittest.mock import MagicMock

from founder_os.strategy.models import CapabilityDefinition
from founder_os.strategy.services.capability_registry_seed_service import (
    REGISTRY_DOMAIN_MAP,
    seed_runtime_registry_capabilities,
    seed_business_pack_capabilities,
    seed_canonical_capability_registry,
)


def _no_existing_rows_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def test_seed_runtime_registry_imports_every_catalog_entry():
    from workforce.agents.capabilities.registry import CAPABILITY_CATALOG

    db = _no_existing_rows_db()
    result = seed_runtime_registry_capabilities(db)

    assert result["inserted"] == len(CAPABILITY_CATALOG)
    assert db.add.call_count == len(CAPABILITY_CATALOG)
    assert db.commit.called

    rows = [call.args[0] for call in db.add.call_args_list]
    assert all(isinstance(r, CapabilityDefinition) for r in rows)
    assert all(r.source == "runtime_registry" for r in rows)
    assert all(r.workspace_id is None and r.brain_id is None for r in rows)
    # Domain must always land in the 5-domain-or-CROSS_DOMAIN vocabulary,
    # never a raw registry.py domain string leaking through.
    assert all(r.domain in {"SALES", "MARKETING", "FINANCE", "LEGAL", "TECH", "CROSS_DOMAIN"} for r in rows)
    assert all(r.risk_level in {"LOW", "MEDIUM", "HIGH", "REGULATED"} for r in rows)

    sales_read = next(r for r in rows if r.capability_key == "sales.crm.read")
    assert sales_read.domain == "SALES"
    assert sales_read.metadata_jsonb["resource"] == "crm"


def test_seed_runtime_registry_preserves_strong_approval_flag():
    db = _no_existing_rows_db()
    seed_runtime_registry_capabilities(db)
    rows = [call.args[0] for call in db.add.call_args_list]

    # finance.payment.transfer is L5 + is_strong_approval=True in the source
    # catalog — this must survive the migration as professional_review_required.
    payment_transfer = next(r for r in rows if r.capability_key == "finance.payment.transfer")
    assert payment_transfer.risk_level == "REGULATED"
    assert payment_transfer.professional_review_required is True
    assert payment_transfer.requires_approval is True


def test_seed_runtime_registry_is_idempotent_and_updates_in_place():
    # A DB that already "has" a matching row for every lookup exercises the
    # update-in-place path exclusively: re-running the seed must never
    # insert a duplicate for an already-imported capability_key. The mock
    # returns the same row for every query regardless of filter args, so its
    # final field values reflect whichever catalog entry was processed last
    # (dict iteration order) rather than any specific key.
    from workforce.agents.capabilities.registry import CAPABILITY_CATALOG

    existing_row = CapabilityDefinition(
        id=1, capability_key="placeholder", source="runtime_registry",
        workspace_id=None, domain="UNSET", risk_level="UNSET",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing_row
    result = seed_runtime_registry_capabilities(db)

    assert result["inserted"] == 0
    assert result["updated"] == len(CAPABILITY_CATALOG)
    assert db.add.call_count == 0

    last_key = list(CAPABILITY_CATALOG.keys())[-1]
    last_cap = CAPABILITY_CATALOG[last_key]
    expected_domain = REGISTRY_DOMAIN_MAP.get(last_cap.domain, "CROSS_DOMAIN")
    assert existing_row.domain == expected_domain  # mutated in place, not re-inserted


def test_seed_business_pack_imports_every_pack_capability():
    from business.packs.loader import BusinessPackLoader

    loader = BusinessPackLoader()
    expected_total = sum(len(loader.list_capabilities(p)) for p in loader.list_factory_pack_ids())

    db = _no_existing_rows_db()
    result = seed_business_pack_capabilities(db)

    assert result["inserted"] == expected_total
    assert expected_total > 0

    rows = [call.args[0] for call in db.add.call_args_list]
    assert all(r.source == "business_pack" for r in rows)
    assert all(r.source_pack_key in loader.list_factory_pack_ids() for r in rows)
    assert all(r.domain in {"SALES", "MARKETING", "FINANCE", "LEGAL", "TECH", "CROSS_DOMAIN"} for r in rows)
    assert all(set(r.content_jsonb.keys()) == {
        "execution_mode", "artifact_type", "required_context", "inputs", "uses", "legal_context", "output"
    } for r in rows)


def test_seed_canonical_capability_registry_runs_both_passes():
    db = _no_existing_rows_db()
    result = seed_canonical_capability_registry(db)

    assert "runtime_registry" in result
    assert "business_pack" in result
    assert result["runtime_registry"]["inserted"] == 41
    assert result["business_pack"]["inserted"] == 48
