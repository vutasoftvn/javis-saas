"""Đối chiếu bảng pin AgentSpec phía Company với catalog Python.

`services/company/operations/services/ai-member.service.ts` pin id/version/hash của
từng profile khi kích hoạt Project team; worker so exact hash với spec Python.
Lệch giữa hai bên làm mọi run của profile đó fail `spec_hash_mismatch` sau deploy.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from apps.cosa.agents.catalog import CATALOG_BY_PROFILE

_SERVICE = (
    Path(__file__).resolve().parents[2]
    / "services/company/operations/services/ai-member.service.ts"
)


def _ts_record(name: str) -> dict[str, str]:
    source = _SERVICE.read_text(encoding="utf-8")
    match = re.search(rf"export const {name}[^=]*=\s*\{{(.*?)\}};", source, re.S)
    assert match, f"{name} not found in {_SERVICE}"
    return dict(re.findall(r"(\w+):\s*\"([^\"]+)\"", match.group(1)))


_IDS = _ts_record("AGENT_PROFILE_SPEC_ID")
_VERSIONS = _ts_record("AGENT_PROFILE_SPEC_VERSION")
_HASHES = _ts_record("AGENT_PROFILE_SPEC_HASH")


def test_company_pin_tables_cover_same_profiles():
    assert set(_IDS) == set(_VERSIONS) == set(_HASHES)


@pytest.mark.parametrize("profile_key", sorted(_IDS))
def test_company_pin_matches_python_catalog(profile_key: str):
    spec = CATALOG_BY_PROFILE[profile_key].agent_spec
    assert (_IDS[profile_key], _VERSIONS[profile_key], _HASHES[profile_key]) == (
        spec.id,
        spec.version,
        spec.compute_hash(),
    )
