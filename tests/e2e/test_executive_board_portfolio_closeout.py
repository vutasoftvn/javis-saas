"""Portfolio-wide closeout regression: prove no functional profile or executive
advisory role silently auto-activates on a brand-new Project.

Plan: .superpowers/sdd/2026-09-12-caio-ai-governance-profile-and-executive-activation/task-5-brief.md

This is the FINAL task (Task 5) of the 8-role Executive Advisory Board portfolio
(cro/sales, vpe/coding, cpo/product, chro/people, ciso/security, gc/legal,
cdo/data, caio/ai_governance). Unlike every prior role's own E2E (which is
role-specific), this test is portfolio-wide: it asserts the negative invariant
that has held true across all 8 roles individually, but had never been checked
in one place as a single regression against a fresh Project.

Mirrors the real HTTP patterns used throughout this portfolio's own E2E suite
(see e.g. `tests/e2e/test_caio_ai_governance_profile.py`): boots against the
existing `real_company_service` fixture (`tests/e2e/conftest.py`), registers a
fresh founder session via `/identity/_e2e/session`, creates a real Project via
`POST /operations/projects`, then reads back the real startup-team roster
(`GET /operations/projects/:projectId/startup-team`) and the real executive
roles list (`GET /operations/projects/:projectId/executive-roles`).
"""

from __future__ import annotations

import time

import httpx

# The 8 new functional profiles introduced across this portfolio (one per role
# plan) — each must start life as a TEMPLATE on a freshly-created project, not
# auto-activated.
_NEW_PROFILE_KEYS = {
    "sales",
    "coding",
    "product",
    "people",
    "security",
    "legal",
    "data",
    "ai_governance",
}

# The 8 executive advisory board roles this portfolio added, each gated behind
# its corresponding profile above becoming ACTIVE first.
_NEW_ROLE_KEYS = {
    "cro",
    "vpe",
    "cpo",
    "chro",
    "ciso",
    "gc",
    "cdo",
    "caio",
}

# Pre-existing roles (present before this 8-role portfolio started) that are
# active-by-default / available out of the box — confirmed against the real
# `shared/contracts/executive-advisor-roles.json` roster, not assumed from the
# plan's own pseudocode (which listed "cco" — verified below to also be
# pre-existing and out of scope for this portfolio's 8 new roles).
_PRE_EXISTING_ROLE_KEYS = {"chief_of_staff", "cfo", "cmo", "coo", "cco"}


def test_new_project_has_all_new_profiles_as_templates_and_no_new_executive_roles_active(
    real_company_service,
):
    """A brand-new Project must start with every one of the 8 new functional
    profiles in TEMPLATE mode, and none of the 8 corresponding executive
    advisory roles reporting ACTIVE — nothing auto-activates anything. This
    does not assert anything new about the pre-existing roles
    (chief_of_staff/cfo/cmo/coo/cco); it only confirms they aren't broken by
    reading their real state through the same roster response."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    reg = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"portfolio-closeout-{time.time()}@example.com",
            "displayName": "Portfolio Closeout Founder",
        },
    )
    assert reg.status_code == 200, reg.text
    data = reg.json()
    token = data["accessToken"]
    workspace_id = str(data["workspaceId"])
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id}

    proj_resp = client.post(
        "/operations/projects",
        json={
            "title": "Portfolio Closeout Project",
            "description": "Fresh project for the 8-role no-auto-activation regression",
        },
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = str(proj_resp.json()["id"])

    # 1. Startup-team roster: every new functional profile must be TEMPLATE.
    roster_resp = client.get(
        f"/operations/projects/{project_id}/startup-team",
        headers=headers,
    )
    assert roster_resp.status_code == 200, roster_resp.text
    roster = roster_resp.json()["items"]

    roster_by_key = {item["profileKey"]: item for item in roster}
    missing_profiles = _NEW_PROFILE_KEYS - roster_by_key.keys()
    assert not missing_profiles, f"expected profiles missing from roster: {missing_profiles}"

    non_template = {
        key: roster_by_key[key]["displayState"]
        for key in _NEW_PROFILE_KEYS
        if roster_by_key[key]["displayState"] != "TEMPLATE"
    }
    assert not non_template, f"profiles unexpectedly not TEMPLATE on a fresh project: {non_template}"

    # 2. Executive roles list: none of the 8 new roles may report ACTIVE.
    roles_resp = client.get(
        f"/operations/projects/{project_id}/executive-roles",
        headers=headers,
    )
    assert roles_resp.status_code == 200, roles_resp.text
    roles = roles_resp.json()["roles"]

    roles_by_key = {role["roleKey"]: role for role in roles}
    missing_roles = _NEW_ROLE_KEYS - roles_by_key.keys()
    assert not missing_roles, f"expected executive roles missing from board: {missing_roles}"

    active_new_roles = {
        key: roles_by_key[key]["displayState"]
        for key in _NEW_ROLE_KEYS
        if roles_by_key[key]["displayState"] == "ACTIVE"
    }
    assert not active_new_roles, f"new executive roles unexpectedly ACTIVE on a fresh project: {active_new_roles}"

    # All 8 new roles must be UNAVAILABLE specifically (their required profile
    # is not yet ACTIVE) — not merely "not ACTIVE" via some other unexpected
    # state such as an error placeholder.
    non_unavailable_new_roles = {
        key: roles_by_key[key]["displayState"]
        for key in _NEW_ROLE_KEYS
        if roles_by_key[key]["displayState"] != "UNAVAILABLE"
    }
    assert not non_unavailable_new_roles, (
        f"new executive roles expected UNAVAILABLE (profile not yet active) on a "
        f"fresh project, got: {non_unavailable_new_roles}"
    )

    # 3. Sanity only — pre-existing roles must still be present in the roster
    # response (this test asserts nothing NEW about their state, just that
    # reading them didn't break).
    present_pre_existing = _PRE_EXISTING_ROLE_KEYS & roles_by_key.keys()
    assert present_pre_existing, (
        "expected at least some pre-existing roles (chief_of_staff/cfo/cmo/coo/cco) "
        f"present in the executive-roles response, got role keys: {sorted(roles_by_key.keys())}"
    )
