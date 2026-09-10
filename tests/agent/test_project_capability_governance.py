"""Tests for project capability governance and scoped delegation."""

from __future__ import annotations

import jwt
import pytest

from apps.cosa.auth.jwt import _get_company_delegation_secret, mint_company_delegation


def test_mint_company_delegation_includes_project_id():
    token = mint_company_delegation(
        sub="user-1",
        workspace_id="ws-1",
        run_id="run-1",
        capability_ids=["operations.task.create_draft"],
        project_id="proj-42",
    )
    secret = _get_company_delegation_secret()
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience="company")

    assert payload["workspace_id"] == "ws-1"
    assert payload["run_id"] == "run-1"
    assert payload["project_id"] == "proj-42"
    assert "operations.task.create_draft" in payload["capability_ids"]


def test_mint_company_delegation_without_project_id():
    token = mint_company_delegation(
        sub="user-1",
        workspace_id="ws-1",
        run_id="run-1",
        capability_ids=["operations.task.list"],
    )
    secret = _get_company_delegation_secret()
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience="company")

    assert payload["workspace_id"] == "ws-1"
    assert payload["run_id"] == "run-1"
    assert "project_id" not in payload
