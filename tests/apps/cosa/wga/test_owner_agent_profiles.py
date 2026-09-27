"""Chặn lệch danh sách owner agent profile giữa company (TS) và worker (Python).

Company `routeOwnerProfile` gán `ownerAgentProfile` cho task WGA; worker phải
có spec chạy được cho MỌI giá trị đó, nếu không task bị block ngay khi sweep.
"""

from __future__ import annotations

import re
from pathlib import Path

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.goal_decomposition import OWNER_AGENT_PROFILES, build_decomposition_prompt
from apps.cosa.worker import wga_run

_CLASSIFIER_TS = (
    Path(__file__).resolve().parents[4]
    / "services/company/operations/services/autonomy-classifier.ts"
)


def _ts_owner_agent_profiles() -> set[str]:
    src = _CLASSIFIER_TS.read_text(encoding="utf-8")
    m = re.search(r"export type OwnerAgentProfile =(.*?);", src, re.S)
    assert m, "OwnerAgentProfile union not found in autonomy-classifier.ts"
    return set(re.findall(r'"([a-z_]+)"', m.group(1)))


def test_python_profiles_match_company_union():
    assert set(OWNER_AGENT_PROFILES) == _ts_owner_agent_profiles()


def test_every_owner_profile_has_runnable_spec():
    for profile in OWNER_AGENT_PROFILES:
        assert profile in AGENT_PROFILE_SPECS, profile
        assert wga_run._SPEC_BY_PROFILE[profile] is AGENT_PROFILE_SPECS[profile]


def test_decomposition_prompt_lists_all_owner_profiles():
    prompt = build_decomposition_prompt("Ship v1", {})
    for profile in OWNER_AGENT_PROFILES:
        assert f"'{profile}'" in prompt


def _ts_prefix_routes() -> list[tuple[str, str]]:
    src = _CLASSIFIER_TS.read_text(encoding="utf-8")
    m = re.search(r"CAP_PREFIX_TO_PROFILE[^=]*=\s*\[(.*?)\n\];", src, re.S)
    assert m, "CAP_PREFIX_TO_PROFILE not found in autonomy-classifier.ts"
    return re.findall(r'\["([^"]+)", "([a-z_]+)"\]', m.group(1))


def _ts_route(cap: str) -> str | None:
    for prefix, profile in _ts_prefix_routes():
        if cap.startswith(prefix):
            return profile
    return None


def test_prefix_routed_capabilities_land_on_a_profile_that_owns_them():
    """Company route theo tiền tố capability; nếu profile đích không có capability
    đó thì worker chặn `capability_not_in_profile` — mọi capability trong catalog
    có tiền tố được route phải về profile sở hữu nó."""
    catalog = wga_run._capability_catalog()
    for profile, caps in catalog.items():
        for cap in caps:
            routed = _ts_route(cap)
            if routed is None:
                continue
            assert cap in catalog.get(routed, []), (cap, profile, routed)


def test_every_specialist_profile_has_a_domain_draft_capability():
    from apps.cosa.capabilities.domain_draft import DOMAIN_DRAFTS

    catalog = wga_run._capability_catalog()
    for d in DOMAIN_DRAFTS:
        assert d.capability_id in catalog[d.profile_key], d
        assert _ts_route(d.capability_id) == d.profile_key, d
