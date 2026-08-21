# ADR-V13-2-005: OKR Key Result Traceability for Opportunities

## Context
Opportunities require linkage to Key Results without schema bloat.

## Decision
Reuse polymorphic `OkrLink` (`strategy/models.py`) with `from_entity_type="opportunity"`, `to_entity_type="key_result"`. Existing `sales_leads.key_result_id` is preserved for backward compatibility.
