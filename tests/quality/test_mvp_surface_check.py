"""Quality tests for MVP capability manifest and surface checker."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.mvp_surface_check import (
    validate_manifest,
    find_runtime_fixture_imports,
    validate_acceptance_ledger,
)


def test_enabled_capability_requires_real_source_and_all_proofs() -> None:
    manifest = {
        "version": "2026-08-31",
        "capabilities": [
            {
                "id": "strategy.canvas.list",
                "enabled": True,
                "owner": "company-operations",
                "plane": "company",
                "method": "GET",
                "path": "/operations/strategy/canvases",
                "schema": "strategy.canvas.list.v1",
                "source_kind": "company_db",
                "requires_workspace": True,
                "frontend_symbol": "StrategyMvpClient.listCanvases",
                "backend_test": "services/company/operations/tests/mvp-canvas-runtime.test.ts",
                "flutter_test": "frontend/test/strategy_mvp_service_test.dart",
                "integration_test": "tests/e2e/test_mvp_strategy_runtime_http.py",
            }
        ],
    }
    assert validate_manifest(manifest) == []


def test_enabled_capability_rejects_runtime_fixture_source() -> None:
    errors = validate_manifest(
        {
            "version": "2026-08-31",
            "capabilities": [
                {
                    "id": "bad",
                    "enabled": True,
                    "owner": "company-operations",
                    "plane": "company",
                    "method": "GET",
                    "path": "/operations/bad",
                    "schema": "bad.v1",
                    "source_kind": "fixture",
                    "requires_workspace": True,
                    "frontend_symbol": "Bad.client",
                    "backend_test": "a",
                    "flutter_test": "b",
                    "integration_test": "c",
                }
            ],
        }
    )
    assert any("source_kind" in e for e in errors)


def test_enabled_capability_rejects_missing_proof_fields() -> None:
    errors = validate_manifest(
        {
            "version": "2026-08-31",
            "capabilities": [
                {
                    "id": "missing.proof",
                    "enabled": True,
                    "owner": "company-operations",
                    "plane": "company",
                    "method": "GET",
                    "path": "/operations/missing",
                    "schema": "missing.v1",
                    "source_kind": "company_db",
                    "requires_workspace": True,
                    "frontend_symbol": "Missing.client",
                    "backend_test": "",
                    "flutter_test": "b",
                    "integration_test": "c",
                }
            ],
        }
    )
    assert any("backend_test" in e for e in errors)


@pytest.mark.parametrize(
    "runtime_import",
    [
        "from tests.fixtures.canvas import CANVAS",
        "import '../test/fixtures/workforce.dart'",
        "from __fixtures__.marketing import sample",
    ],
)
def test_runtime_fixture_import_is_rejected(runtime_import: str, tmp_path: Path) -> None:
    runtime_file = tmp_path / "runtime.py"
    runtime_file.write_text(runtime_import)
    assert len(find_runtime_fixture_imports(tmp_path)) > 0


def test_acceptance_ledger_validation_flags_missing_proofs(tmp_path: Path) -> None:
    ledger_file = tmp_path / "ledger.md"
    ledger_file.write_text(
        "| capability_id | owner | source_kind | contract_schema | backend_test | flutter_test | integration_test | status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| workforce.agent.list | agent-platform | agent_db | workforce.agent.list.v1 | tests/apps/cosa/test_workforce_routes.py | frontend/test/workforce_service_test.dart |  | PLANNED |\n"
    )
    manifest = {
        "version": "2026-08-31",
        "capabilities": [
            {
                "id": "workforce.agent.list",
                "enabled": True,
                "owner": "agent-platform",
                "plane": "agent",
                "method": "GET",
                "path": "/agent/workforce/agents",
                "schema": "workforce.agent.list.v1",
                "source_kind": "agent_db",
                "requires_workspace": True,
                "frontend_symbol": "WorkforceService.listAgents",
                "backend_test": "tests/apps/cosa/test_workforce_routes.py",
                "flutter_test": "frontend/test/workforce_service_test.dart",
                "integration_test": "tests/e2e/test_mvp_workforce_http.py",
            }
        ],
    }
    errors = validate_acceptance_ledger(ledger_file, manifest)
    assert any("integration_test" in e for e in errors)
