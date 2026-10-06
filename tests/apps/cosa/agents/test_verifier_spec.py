from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.catalog import CATALOG_BY_PROFILE
from apps.cosa.agents.specs import COSA_VERIFIER_AGENT_SPEC


def test_verifier_spec_is_read_only_and_internal():
    spec = COSA_VERIFIER_AGENT_SPEC
    assert spec.id == "cosa.agents.verifier"
    assert list(spec.capability_refs) == []
    assert spec.prompt_ref is not None
    entry = CATALOG_BY_PROFILE["verifier"]
    assert entry.availability == "deployed_not_public"
    assert entry.deployment_kind == "system"
    assert entry.agent_spec.id == spec.id


def test_verifier_is_not_a_public_profile():
    assert "verifier" not in AGENT_PROFILE_SPECS
