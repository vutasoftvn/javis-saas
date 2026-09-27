"""Parity cấp phép agent (ADR-CHAT-ACTIONS-001) giữa apps/cosa và company:

1. Bảng TS `AGENT_PROFILE_GRANTED_CAPABILITIES` = capability ghi (T1/T2 có AGENT_CAP) trong spec
   của profile — trừ `finance.transaction.record` (hạn mức chưa chốt, founder cấp tay).
2. Mọi capability ghi qua company có binding permission (migration identity) — thiếu thì company
   không cấp được live authorization ticket.
3. Backfill grant (operations 030) khớp đúng bảng TS.
4. Binding compliance của `cosa.agents.operations` phủ đúng tập ComplianceResolver xin — thiếu 1
   capability là 404 cho cả run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from agent.contracts.run import RunRequest

from apps.cosa.agents.catalog import CATALOG_BY_PROFILE
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.capabilities.access_matrix import MATRIX, Tier
from apps.cosa.compliance.contracts import AiComplianceUnavailable, ComplianceDenied
from apps.cosa.compliance.resolver import ComplianceResolver

COMPANY = Path(__file__).resolve().parents[3] / "services/company"
NOT_AUTO_GRANTED = {"finance.transaction.record"}


def _ts_grant_table() -> dict[str, set[str]]:
    text = (COMPANY / "operations/services/agent-profile-grants.service.ts").read_text()
    body = text[text.index("AGENT_PROFILE_GRANTED_CAPABILITIES") :]
    body = body[: body.index("});") + 3]
    return {
        profile: set(re.findall(r'"([a-z_.]+)"', caps))
        for profile, caps in re.findall(r"(\w+): Object\.freeze\(\[(.*?)\]\)", body, re.S)
    }


def _owner_profiles() -> set[str]:
    text = (COMPANY / "operations/services/ai-member.service.ts").read_text()
    body = text[text.index("export const AGENT_PROFILE_SPEC_ID") :]
    body = body[: body.index("};")]
    return set(re.findall(r"^\s+(\w+):", body, re.M))


def _company_writes() -> set[str]:
    return {
        cap
        for cap, e in MATRIX.items()
        if e.company_agent_cap and e.tier in (Tier.T1_DRAFT, Tier.T2_COMMIT)
    }


def test_ts_grant_table_matches_profile_specs() -> None:
    expected = {}
    for profile in _owner_profiles():
        caps = set(CATALOG_BY_PROFILE[profile].agent_spec.capability_refs) & _company_writes()
        caps -= NOT_AUTO_GRANTED
        if caps:
            expected[profile] = caps
    assert _ts_grant_table() == expected


def test_every_company_write_capability_has_a_permission_binding() -> None:
    sql = "\n".join(
        p.read_text() for p in sorted((COMPANY / "identity/migrations").glob("*.up.sql"))
    )
    bound = set(re.findall(r"\('([a-z_.]+)',\s*'[a-z_.]+',\s*'[A-Z_]+',\s*\d+\)", sql))
    missing = sorted(_company_writes() - bound)
    assert not missing, f"capability ghi thiếu binding permission: {missing}"


def test_backfill_migration_matches_ts_grant_table() -> None:
    sql = (
        COMPANY / "operations/migrations/030_backfill_agent_capability_grants.up.sql"
    ).read_text()
    pairs: dict[str, set[str]] = {}
    for profile, cap in re.findall(r"\('(\w+)', '([a-z_.]+)'\)", sql):
        pairs.setdefault(profile, set()).add(cap)
    assert pairs == _ts_grant_table()


class _Capture:
    def __init__(self) -> None:
        self.capability_ids: list[str] = []

    async def resolve_snapshot(self, **kwargs):  # noqa: ANN003, ANN201
        self.capability_ids = list(kwargs["capability_ids"])
        raise AiComplianceUnavailable("NOT_READY")


@pytest.mark.asyncio
async def test_compliance_bindings_cover_operations_spec_request() -> None:
    capture = _Capture()
    request = RunRequest(
        root_executable_ref="agent:cosa.agents.operations",
        workspace_id="ws_1",
        principal="user:1",
        input={"prompt": "x"},
    )
    with pytest.raises(ComplianceDenied):
        await ComplianceResolver(capture).resolve_for_run(request, COSA_OPERATIONS_AGENT_SPEC)

    bound: set[str] = set()
    for path in sorted((COMPANY / "finance-legal/migrations").glob("*.up.sql")):
        sql = path.read_text()
        if "system_key = 'cosa.agents.operations'" in sql:
            bound |= set(re.findall(r"\('([a-z_.\-]+)', '(?:READ|DRAFT|EXTERNAL)'", sql))
    missing = sorted(set(capture.capability_ids) - bound)
    assert not missing, f"thiếu binding compliance cho cosa.agents.operations: {missing}"
