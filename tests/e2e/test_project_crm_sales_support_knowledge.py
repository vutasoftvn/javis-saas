"""E2E Verification for Project CRM Foundation, Tenant Isolation, and Sales Agent Capability.

Entry evidence for CRO Executive Role Activation:
Plan: docs/superpowers/plans/2026-09-11-project-crm-and-sales-support-knowledge.md
Roadmap: docs/superpowers/plans/2026-09-12-executive-board-remaining-roles-roadmap.md
"""

from __future__ import annotations

import asyncio
import os
import time
import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.project_crm_read import create_project_crm_read_handler
from apps.cosa.agents.specs import COSA_SALES_AGENT_SPEC
from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS

_SERVICE_TOKEN = os.environ.get(
    "COSA_WORKER_SERVICE_TOKEN",
    "dev-worker-service-token",
)


@pytest.fixture
def crm_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B with Project B1."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Founder A / Workspace A
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"crm-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CRM Alpha Project", "description": "Testing CRM foundation"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Founder B / Workspace B
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"crm-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
    )
    assert reg_b.status_code == 200, reg_b.text
    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": ws_b}

    # Project B1
    p_b_resp = client.post(
        "/operations/projects",
        json={"title": "CRM Beta Project", "description": "Workspace B project"},
        headers=headers_b,
    )
    assert p_b_resp.status_code == 200, p_b_resp.text
    proj_b_id = str(p_b_resp.json()["id"])

    return {
        "base_url": base_url,
        "ws_a": ws_a,
        "headers_a": headers_a,
        "proj_a_id": proj_a_id,
        "ws_b": ws_b,
        "headers_b": headers_b,
        "proj_b_id": proj_b_id,
    }


def test_project_crm_isolation_and_lifecycle(crm_test_env):
    """Test full Project CRM CRUD, custom schema, and strict tenant isolation."""
    base_url = crm_test_env["base_url"]
    headers_a = crm_test_env["headers_a"]
    headers_b = crm_test_env["headers_b"]
    proj_a_id = crm_test_env["proj_a_id"]
    proj_b_id = crm_test_env["proj_b_id"]
    ws_a = crm_test_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Create Lead Source in Project A1
    src_resp = client.post(
        f"/commercial/projects/{proj_a_id}/crm/lead-sources",
        json={
            "sourceType": "landing_form",
            "label": "Main Landing Form",
        },
        headers=headers_a,
    )
    assert src_resp.status_code == 200, src_resp.text
    src_data = src_resp.json()
    assert src_data["label"] == "Main Landing Form"
    source_id = str(src_data["id"])

    # 2. Create Lead Field Definition in Project A1
    field_resp = client.post(
        f"/commercial/projects/{proj_a_id}/crm/field-definitions",
        json={
            "stableKey": "company_size",
            "label": "Company Size",
            "dataType": "SHORT_TEXT",
            "classification": "BUSINESS_CONFIDENTIAL",
            "requiredAtStages": ["QUALIFIED"],
        },
        headers=headers_a,
    )
    assert field_resp.status_code == 200, field_resp.text
    field_data = field_resp.json()
    assert field_data["stableKey"] == "company_size"
    assert field_data["status"] == "ACTIVE"

    # 3. Create Lead in Project A1
    lead_resp = client.post(
        f"/commercial/projects/{proj_a_id}/crm/leads",
        json={
            "name": "Alex Founder",
            "email": "alex@startup.test",
            "phone": "+84901234567",
            "company": "Acme Corp",
            "leadSourceId": source_id,
            "fieldValues": {
                "company_size": "10-50",
            },
            "consent": {
                "purpose": "early_access_followup",
                "lawfulBasis": "CONSENT",
                "policyVersion": "2026-09-11",
            },
        },
        headers=headers_a,
    )
    assert lead_resp.status_code == 200, lead_resp.text
    lead_data = lead_resp.json()
    assert lead_data["name"] == "Alex Founder"
    assert lead_data["projectId"] == proj_a_id
    assert lead_data["fieldValues"]["company_size"] == "10-50"
    lead_id = str(lead_data["id"])

    # 4. List Leads in Project A1
    list_resp = client.get(
        f"/commercial/projects/{proj_a_id}/crm/leads",
        headers=headers_a,
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()["leads"]
    assert any(item["id"] == lead_id for item in items)

    # 5. Strict Cross-Tenant Isolation: Workspace B cannot read Project A1's leads or schema
    denied_leads = client.get(
        f"/commercial/projects/{proj_a_id}/crm/leads",
        headers=headers_b,
    )
    assert denied_leads.status_code in (403, 404), denied_leads.text

    denied_fields = client.get(
        f"/commercial/projects/{proj_a_id}/crm/schema",
        headers=headers_b,
    )
    assert denied_fields.status_code in (403, 404), denied_fields.text

    # 6. Verify Python Agent Capability project.crm.read works with real company service
    cosa_client = CompanyServiceClient(base_url=base_url, headers=headers_a)
    crm_read_handler = create_project_crm_read_handler(cosa_client)

    agent_result = asyncio.run(
        crm_read_handler(
            {"project_id": proj_a_id},
            {"workspace_id": ws_a},
        )
    )
    assert agent_result["projectId"] == proj_a_id
    assert len(agent_result["leads"]) >= 1
    assert any(l["id"] == lead_id for l in agent_result["leads"])
    assert len(agent_result["fieldDefinitions"]) >= 1


def test_sales_agent_spec_integrity():
    """Verify COSA_SALES_AGENT_SPEC contract, autonomy level, and hash binding."""
    spec = AGENT_PROFILE_SPECS["sales"]
    assert spec is COSA_SALES_AGENT_SPEC
    assert spec.id == "cosa.agents.sales"
    assert spec.version == "1.0.0"
    assert "project.crm.read" in spec.capability_refs
    assert "engagement.message.send" not in spec.capability_refs
    assert "finance.transaction.record" not in spec.capability_refs
    assert spec.compute_hash() == "089a67c81dc22041835b0ed05df7a441305c6abe416f293f609cc5262d31f332"
