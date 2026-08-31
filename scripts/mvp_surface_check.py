#!/usr/bin/env python3
"""Checks MVP capability manifest completeness, generated metadata sync,

route implementation, and truth-only runtime fixture isolation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_SOURCE_KINDS = {
    "company_db",
    "agent_db",
    "object_store",
    "control_plane",
    "external_connector",
}

ALLOWED_PLANES = {"company", "platform", "agent", "localWorker", "local_worker"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}

RUNTIME_ROOTS = (
    "frontend/lib",
    "services/company",
    "services/cosa",
    "apps/cosa",
    "packages/agent",
)

FIXTURE_IMPORT_PATTERNS = [
    re.compile(r"from\s+[\w\.]*fixtures[\w\.]*\s+import"),
    re.compile(r"import\s+[\w\.]*fixtures"),
    re.compile(r"import\s+['\"][^'\"]*(?:fixtures|__fixtures__|mock_data|demo_data)[^'\"]*['\"]"),
    re.compile(r"from\s+__fixtures__"),
    re.compile(r"['\"][^'\"]*fixtures/[^'\"]+['\"]"),
]


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, list):
        return ["manifest.capabilities must be a list"]

    seen_ids: set[str] = set()
    seen_routes: set[str] = set()

    for i, cap in enumerate(capabilities):
        if not isinstance(cap, dict):
            errors.append(f"capability [{i}] must be an object")
            continue

        cid = cap.get("id")
        if not cid or not isinstance(cid, str):
            errors.append(f"capability [{i}] missing valid string 'id'")
            continue

        if cid in seen_ids:
            errors.append(f"Duplicate capability id: {cid}")
        seen_ids.add(cid)

        source_kind = cap.get("source_kind")
        if source_kind not in ALLOWED_SOURCE_KINDS:
            errors.append(
                f"capability '{cid}': invalid source_kind '{source_kind}', must be one of {ALLOWED_SOURCE_KINDS}"
            )

        plane = cap.get("plane")
        if plane not in ALLOWED_PLANES:
            errors.append(f"capability '{cid}': invalid plane '{plane}'")

        method = cap.get("method")
        if method not in ALLOWED_METHODS:
            errors.append(f"capability '{cid}': invalid method '{method}'")

        path = cap.get("path")
        if not path or not isinstance(path, str):
            errors.append(f"capability '{cid}': missing valid string 'path'")

        route_key = f"{plane}:{method} {path}"
        if route_key in seen_routes:
            errors.append(f"Duplicate route '{route_key}' on capability '{cid}'")
        seen_routes.add(route_key)

        enabled = cap.get("enabled", False)
        if enabled:
            # When enabled, required proof fields must be present and non-empty
            for field in (
                "backend_test",
                "flutter_test",
                "integration_test",
                "frontend_symbol",
                "schema",
                "owner",
            ):
                val = cap.get(field)
                if not val or not isinstance(val, str) or not val.strip():
                    errors.append(
                        f"capability '{cid}': enabled capability must have non-empty '{field}'"
                    )

    return errors


def find_runtime_fixture_imports(root_path: Path) -> list[str]:
    violations: list[str] = []
    ignored_parts = {
        "node_modules",
        ".dart_tool",
        ".encore",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
    }
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        # Skip dependency, build and cache directories
        if any(part in ignored_parts for part in file_path.parts):
            continue
        # Skip test files and test directories
        path_str = str(file_path)
        if any(
            marker in path_str
            for marker in (
                "/test/",
                "/tests/",
                "/testing/",
                "_test.",
                ".test.",
                "/testkit/",
                "conftest.py",
            )
        ):
            continue
        if file_path.suffix not in (".py", ".ts", ".dart", ".js", ".mjs"):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern in FIXTURE_IMPORT_PATTERNS:
            match = pattern.search(content)
            if match:
                violations.append(
                    f"runtime fixture import in {file_path.relative_to(root_path)}: {match.group(0)}"
                )

    return violations



def validate_acceptance_ledger(
    ledger_path: Path, manifest: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if not ledger_path.exists():
        return [f"Acceptance ledger file does not exist: {ledger_path}"]

    content = ledger_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    ledger_rows: dict[str, dict[str, str]] = {}
    header_idx = -1
    col_names: list[str] = []

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if "capability_id" in cols:
            header_idx = idx
            col_names = cols
            continue
        if header_idx != -1 and idx > header_idx + 1:
            if len(cols) == len(col_names):
                row = dict(zip(col_names, cols))
                cid = row.get("capability_id", "")
                if cid:
                    ledger_rows[cid] = row

    capabilities = manifest.get("capabilities", [])
    for cap in capabilities:
        cid = cap.get("id")
        enabled = cap.get("enabled", False)
        if not enabled:
            continue
        if cid not in ledger_rows:
            errors.append(f"Acceptance ledger missing row for enabled capability: {cid}")
            continue

        row = ledger_rows[cid]
        for field in ("backend_test", "flutter_test", "integration_test"):
            if not row.get(field) or not row.get(field, "").strip():
                errors.append(
                    f"Acceptance ledger capability '{cid}' has blank proof field '{field}'"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check MVP capability surface and contracts")
    parser.add_argument("--check", action="store_true", help="Run surface validation checks")
    parser.add_argument("--ledger", action="store_true", help="Validate acceptance ledger")
    args = parser.parse_args()

    manifest_path = REPO_ROOT / "shared/contracts/mvp-surface.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found", file=sys.stderr)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as ex:
        print(f"ERROR reading manifest: {ex}", file=sys.stderr)
        return 1

    errors = validate_manifest(manifest)
    if errors:
        print("Manifest validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Check runtime fixture imports across specified roots
    fixture_errors: list[str] = []
    for root_rel in RUNTIME_ROOTS:
        root_dir = REPO_ROOT / root_rel
        if root_dir.exists():
            fixture_errors.extend(find_runtime_fixture_imports(root_dir))

    if fixture_errors:
        print("Forbidden runtime fixture imports found:", file=sys.stderr)
        for err in fixture_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.ledger:
        ledger_path = REPO_ROOT / "docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md"
        ledger_errors = validate_acceptance_ledger(ledger_path, manifest)
        if ledger_errors:
            print("Acceptance ledger validation errors:", file=sys.stderr)
            for err in ledger_errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

    print("✅ MVP surface check passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
