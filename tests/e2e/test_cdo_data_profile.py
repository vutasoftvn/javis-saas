"""E2E Verification for CDO Data Profile and Executive Role Activation.

Plan: .superpowers/sdd/2026-09-12-cdo-data-profile-and-executive-activation/task-3-brief.md
Mirrors: tests/e2e/test_gc_legal_profile.py (freshest sibling, hardened body-content assertions).
"""

from __future__ import annotations

import os
import time
import httpx
import pytest

_SERVICE_TOKEN = os.environ.get(
    "COSA_WORKER_SERVICE_TOKEN",
    "dev-worker-service-token",
)


@pytest.fixture
def cdo_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"cdo-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CDO Alpha Project", "description": "Data project for CDO"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"cdo-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
    )
    assert reg_b.status_code == 200, reg_b.text
    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": ws_b}

    return {
        "base_url": base_url,
        "ws_a": ws_a,
        "headers_a": headers_a,
        "token_a": token_a,
        "proj_a_id": proj_a_id,
        "ws_b": ws_b,
        "headers_b": headers_b,
    }


@pytest.mark.cross_plane
def test_cdo_activation_boundary_and_deliberation(advisor_stack, advisor_cluster):
    """Đường đầy đủ của role CDO trên stack thật: profile nền -> office Workspace ->
    Project deployment -> stage gate -> frame với pin overlay; cross-tenant bị từ chối."""
    from tests.e2e.advisor_board import run_role_lifecycle

    run_role_lifecycle(advisor_stack, advisor_cluster, "cdo", "Do we have enough classified data governance evidence to justify adopting the new data lake now?")



def test_data_governance_dossier_is_project_and_workspace_isolated(cdo_test_env):
    """Founder A creates a data governance dossier on Project A1; Workspace B
    cannot read it."""
    headers_a = cdo_test_env["headers_a"]
    headers_b = cdo_test_env["headers_b"]
    proj_a_id = cdo_test_env["proj_a_id"]
    base_url = cdo_test_env["base_url"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # Founder A creates a data governance dossier on Project A1
    create_resp = client.post(
        "/operations/data-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "assets": [
                {"assetId": "asset-customer-events", "classification": "INTERNAL", "qualityStatus": "VALIDATED"}
            ],
            "sourceRefs": [{"sourceRef": "catalog:customer-events-v1", "classification": "INTERNAL"}],
            "reasonCode": "ASSET_CATALOGED",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 200, create_resp.text
    dossier = create_resp.json()
    assert dossier["revision"] == 1
    assert dossier["status"] == "DRAFT"

    # Founder A can read it back on Project A1
    read_a_resp = client.get(
        f"/operations/projects/{proj_a_id}/data-governance-dossier",
        headers=headers_a,
    )
    assert read_a_resp.status_code == 200, read_a_resp.text
    assert read_a_resp.json()["dossierId"] == dossier["dossierId"]

    # Workspace B (a different tenant) cannot read the dossier on Project A1
    read_b_resp = client.get(
        f"/operations/projects/{proj_a_id}/data-governance-dossier",
        headers=headers_b,
    )
    assert read_b_resp.status_code in (403, 404), read_b_resp.text
    # Không chỉ kiểm tra status code chung chung — xác nhận đúng loại từ chối
    # là "project không thuộc workspace" (permission_denied), không phải một
    # lỗi 4xx bất kỳ khác vô tình khớp status code.
    read_b_body = read_b_resp.json()
    assert read_b_body.get("code") == "permission_denied", read_b_resp.text
    assert "PROJECT_ACCESS_DENIED" in read_b_body.get("message", ""), read_b_resp.text


def test_data_governance_dossier_rejects_raw_uri_and_field_sample_shaped_field(cdo_test_env):
    """Data Governance Dossier's headline property: raw values/raw file URIs/
    credentials/field-samples are never allowed — reject with 400 and a
    body-content marker proving the specific rejection reason.

    Note: the embedding-vector-shaped rejection (DATA_DOSSIER_EMBEDDING_REJECTED)
    exists in the service's deep-scan (data-governance-dossier.service.ts
    deepAssertSafeShape) but is NOT reachable through this real typed HTTP
    endpoint — every field on DataAsset/DataSourceRef is declared as `string`
    in the Encore-typed request body, so a JSON array value is rejected by
    Encore's request decoder ("invalid type: sequence, expected a string")
    before the request ever reaches the service's own deep-scan. Task 1's own
    unit test only reaches that branch by calling the service function
    directly with an `as never` cast that bypasses the typed HTTP contract.
    This mirrors GC's Task 3 own-review finding style: documented here and in
    this plan's Known Limitations rather than asserted as covered."""
    headers_a = cdo_test_env["headers_a"]
    proj_a_id = cdo_test_env["proj_a_id"]
    base_url = cdo_test_env["base_url"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # A field-sample-shaped string (delimited data row) tucked into a
    # sourceRef's redactedExcerpt must be rejected.
    create_resp_field_sample = client.post(
        "/operations/data-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "sourceRefs": [
                {
                    "sourceRef": "catalog:customer-export",
                    "redactedExcerpt": "john,doe,42,new-york,555-1234",
                }
            ],
            "reasonCode": "ASSET_CATALOGED",
        },
        headers=headers_a,
    )
    assert create_resp_field_sample.status_code == 400, create_resp_field_sample.text
    create_body_field_sample = create_resp_field_sample.json()
    assert create_body_field_sample.get("code") == "invalid_argument", create_resp_field_sample.text
    assert "DATA_DOSSIER_FIELD_SAMPLE_REJECTED" in create_body_field_sample.get("message", ""), (
        create_resp_field_sample.text
    )

    # A raw file URI (S3 path) tucked into a sourceRef's redactedExcerpt must
    # be rejected with the specific raw-URI rejection marker.
    create_resp_uri = client.post(
        "/operations/data-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "sourceRefs": [
                {
                    "sourceRef": "catalog:raw-file-source",
                    "redactedExcerpt": "s3://prod-customer-data/raw/events.parquet",
                }
            ],
            "reasonCode": "ASSET_CATALOGED",
        },
        headers=headers_a,
    )
    assert create_resp_uri.status_code == 400, create_resp_uri.text
    create_body_uri = create_resp_uri.json()
    assert create_body_uri.get("code") == "invalid_argument", create_resp_uri.text
    assert "DATA_DOSSIER_RAW_URI_REJECTED" in create_body_uri.get("message", ""), create_resp_uri.text
