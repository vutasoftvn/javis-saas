"""Quality tests for MVP capability manifest and surface checker."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.mvp_surface_check import (
    find_runtime_fixture_imports,
    validate_manifest,
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
                "backend_test": "services/company/operations/tests/strategy-experiment-services.test.ts",
                "flutter_test": "frontend/test/modules/strategy/strategy_controller_test.dart",
                "integration_test": "tests/e2e/test_mvp_strategy_runtime_http.py",
            }
        ],
    }
    assert validate_manifest(manifest) == []


def test_enabled_capability_rejects_nonexistent_proof_paths() -> None:
    errors = validate_manifest(
        {
            "version": "2026-08-31",
            "capabilities": [
                {
                    "id": "x",
                    "enabled": True,
                    "owner": "company-operations",
                    "plane": "company",
                    "method": "GET",
                    "path": "/operations/x",
                    "schema": "x.v1",
                    "source_kind": "company_db",
                    "requires_workspace": True,
                    "frontend_symbol": "X.client",
                    "backend_test": "services/company/missing_backend.ts",
                    "flutter_test": "frontend/test/missing_test.dart",
                    "integration_test": "tests/e2e/missing.py",
                }
            ],
        }
    )
    assert "does not exist" in "\n".join(errors)


def test_enabled_capability_rejects_empty_integration_test() -> None:
    errors = validate_manifest(
        {
            "version": "2026-08-31",
            "capabilities": [
                {
                    "id": "x",
                    "enabled": True,
                    "owner": "company-operations",
                    "plane": "company",
                    "method": "GET",
                    "path": "/operations/x",
                    "schema": "x.v1",
                    "source_kind": "company_db",
                    "requires_workspace": True,
                    "frontend_symbol": "X.client",
                    "backend_test": "services/company/operations/tests/mvp-canvas-runtime.test.ts",
                    "flutter_test": "frontend/test/modules/strategy/strategy_controller_test.dart",
                    "integration_test": "",
                }
            ],
        }
    )
    assert any("integration_test" in e for e in errors)


def test_disabled_capability_permitted_to_omit_ui_proof() -> None:
    errors = validate_manifest(
        {
            "version": "2026-08-31",
            "capabilities": [
                {
                    "id": "disabled.route",
                    "enabled": False,
                    "owner": "company-operations",
                    "plane": "company",
                    "method": "GET",
                    "path": "/operations/disabled",
                    "schema": "disabled.v1",
                    "source_kind": "company_db",
                    "requires_workspace": True,
                }
            ],
        }
    )
    assert errors == []


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


def test_runtime_fixture_metadata_is_not_an_import(tmp_path: Path) -> None:
    runtime_file = tmp_path / "runtime.ts"
    runtime_file.write_text(
        'export const evidence = { note: "Fixtures stored in tests/fixtures/cas-so/" };\n'
    )

    assert find_runtime_fixture_imports(tmp_path) == []


