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
