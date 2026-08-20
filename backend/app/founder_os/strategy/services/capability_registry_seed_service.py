"""Seeds the canonical Capability Registry (G1 §4 / G3 Phase 1B) from the two
sources that used to be separate, competing `CapabilityDefinition` shapes:

- `workforce/agents/capabilities/registry.py::CAPABILITY_CATALOG` — this one
  actually drives runtime authorization (CapabilityGateway), so its 41
  entries become the canonical source of truth for risk_level/
  requires_approval once seeded; registry.py itself is deleted after this
  redirect lands.
- `business/packs/factory/*/capabilities/*.yaml`, read through the existing
  `BusinessPackLoader` (not by re-parsing YAML here) — 11 packs, 48 files.
  The live Business Packs Store request path keeps reading YAML directly
  for now (working, override-aware, zero regression risk); this seed makes
  the same data ALSO queryable from one canonical table for cross-cutting
  capability inventory purposes. Swapping the pack-serving path itself onto
  this table is a mechanical follow-up, not required for this merge.

Idempotent: re-running upserts by (capability_key, source, workspace_id IS
NULL), never creates duplicate rows.

Domain mapping to the 5 Core Domain Agent vocabulary (already live on
FounderDecision.domain) is a first-pass, deliberately conservative
best-effort — anything that doesn't cleanly map to one of the 5 domains
gets CROSS_DOMAIN rather than a guessed assignment. It's a plain Python
dict, trivially adjustable later; it does not create or rename any Agent
(G1 DO NOT list item #4).
"""
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.founder_os.strategy.models import CapabilityDefinition

# workforce/agents/capabilities/registry.py domain -> 5-domain vocabulary
REGISTRY_DOMAIN_MAP: dict[str, str] = {
    "sales": "SALES",
    "finance": "FINANCE",
    "marketing": "MARKETING",
    "legal": "LEGAL",
    "code": "TECH",
    "communication": "CROSS_DOMAIN",
    "project": "CROSS_DOMAIN",
    "automation": "CROSS_DOMAIN",
    "learning": "CROSS_DOMAIN",
    "strategy": "CROSS_DOMAIN",
    "system": "CROSS_DOMAIN",
    "web": "CROSS_DOMAIN",
}

# registry.py's RiskLevel (L0-L5) -> this table's existing LOW/MEDIUM/HIGH/REGULATED
REGISTRY_RISK_LEVEL_MAP: dict[str, str] = {
    "L0": "LOW",
    "L1": "LOW",
    "L2": "LOW",
    "L3": "MEDIUM",
    "L4": "HIGH",
    "L5": "REGULATED",
}

# business pack id -> 5-domain vocabulary. Only 4 of the 11 packs map
# cleanly onto one of the 5 Core Domain Agents; the rest (customer,
# governance, growth, operations, people, reporting, training) are
# cross-cutting by nature and get CROSS_DOMAIN rather than a forced fit.
PACK_DOMAIN_MAP: dict[str, str] = {
    "finance": "FINANCE",
    "marketing": "MARKETING",
    "sales": "SALES",
    "product-tech": "TECH",
    "customer": "CROSS_DOMAIN",
    "governance": "CROSS_DOMAIN",
    "growth": "CROSS_DOMAIN",
    "operations": "CROSS_DOMAIN",
    "people": "CROSS_DOMAIN",
    "reporting": "CROSS_DOMAIN",
    "training": "CROSS_DOMAIN",
}

# business pack risk.level (low/medium/high) -> this table's vocabulary.
# "critical"/"regulated" isn't used by any current pack YAML but mapped for
# completeness/forward-compat.
PACK_RISK_LEVEL_MAP: dict[str, str] = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "REGULATED",
    "regulated": "REGULATED",
}


def _upsert(db: Session, *, capability_key: str, source: str, fields: dict[str, Any]) -> bool:
    """Returns True if a new row was inserted, False if an existing one was updated."""
    existing = (
        db.query(CapabilityDefinition)
        .filter(
            CapabilityDefinition.capability_key == capability_key,
            CapabilityDefinition.source == source,
            CapabilityDefinition.workspace_id.is_(None),
        )
        .first()
    )
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        return False

    db.add(CapabilityDefinition(
        id=generate_snowflake_id(),
        workspace_id=None,
        brain_id=None,
        capability_key=capability_key,
        source=source,
        **fields,
    ))
    return True


def seed_runtime_registry_capabilities(db: Session) -> dict[str, int]:
    """Imports CAPABILITY_CATALOG into capability_definitions. Call this
    once (e.g. at startup, like the entitlement snapshot reload) before
    redirecting CapabilityGateway/the /catalog endpoint to query the DB."""
    from app.workforce.agents.capabilities.registry import CAPABILITY_CATALOG

    inserted = updated = 0
    for key, cap in CAPABILITY_CATALOG.items():
        risk_value = cap.risk_level.value if hasattr(cap.risk_level, "value") else str(cap.risk_level)
        permission_value = cap.permission_level.value if hasattr(cap.permission_level, "value") else str(cap.permission_level)
        fields = dict(
            name=cap.name,
            description=cap.description or "",
            domain=REGISTRY_DOMAIN_MAP.get(cap.domain, "CROSS_DOMAIN"),
            status="ACTIVE",
            risk_level=REGISTRY_RISK_LEVEL_MAP.get(risk_value, "MEDIUM"),
            requires_approval=bool(cap.requires_approval),
            professional_review_required=bool(cap.is_strong_approval),
            metadata_jsonb={
                "resource": cap.resource,
                "action": cap.action,
                "permission_level": permission_value,
                "original_risk_level": risk_value,
                "original_domain": cap.domain,
            },
        )
        if _upsert(db, capability_key=key, source="runtime_registry", fields=fields):
            inserted += 1
        else:
            updated += 1

    db.commit()
    return {"inserted": inserted, "updated": updated}


def seed_business_pack_capabilities(db: Session, loader: Optional[Any] = None) -> dict[str, int]:
    """Imports every business pack's capability YAML (via the existing
    BusinessPackLoader — never re-parses YAML directly) into
    capability_definitions with source="business_pack". Does not change
    business/packs' own live request path (still reads YAML directly,
    override-aware); this is an additive registry mirror."""
    from app.business.packs.loader import BusinessPackLoader

    loader = loader or BusinessPackLoader()
    inserted = updated = 0

    for pack_id in loader.list_factory_pack_ids():
        for cap in loader.list_capabilities(pack_id):
            risk_level_raw = cap.risk.level if cap.risk else "low"
            fields = dict(
                name=cap.name.get("en") or cap.name.get("vi") or cap.id,
                description=cap.name.get("vi") or cap.name.get("en") or "",
                domain=PACK_DOMAIN_MAP.get(pack_id, "CROSS_DOMAIN"),
                status="ACTIVE",
                source_pack_key=pack_id,
                risk_level=PACK_RISK_LEVEL_MAP.get(str(risk_level_raw).lower(), "MEDIUM"),
                requires_approval=bool(cap.risk.admin_review) if cap.risk else False,
                professional_review_required=bool(cap.risk.admin_review) if cap.risk else False,
                content_jsonb={
                    "execution_mode": cap.execution_mode,
                    "artifact_type": cap.artifact_type,
                    "required_context": cap.required_context,
                    "inputs": cap.inputs,
                    "uses": cap.uses.model_dump() if hasattr(cap.uses, "model_dump") else cap.uses,
                    "legal_context": cap.legal_context.model_dump() if hasattr(cap.legal_context, "model_dump") else cap.legal_context,
                    "output": cap.output.model_dump() if hasattr(cap.output, "model_dump") else cap.output,
                },
            )
            if _upsert(db, capability_key=cap.id, source="business_pack", fields=fields):
                inserted += 1
            else:
                updated += 1

    db.commit()
    return {"inserted": inserted, "updated": updated}


def seed_canonical_capability_registry(db: Session) -> dict[str, dict[str, int]]:
    """Runs both seed passes. Safe to call on every startup — fully idempotent."""
    return {
        "runtime_registry": seed_runtime_registry_capabilities(db),
        "business_pack": seed_business_pack_capabilities(db),
    }
