#!/usr/bin/env python3
"""Runner cho Vitest integration tests trên disposable PostgreSQL cluster.

Sử dụng:
    .venv/bin/python scripts/run_business_audit_tests.py company|cosa <vitest-file>...

Đặc tả:
    - Tạo cluster mới ngẫu nhiên (secrets.token_hex(8))
    - Áp dụng migrations Agent -> COSA -> Company
    - Chạy npx vitest run <test_files> với child_env có disposable URLs
    - Truyền nguyên exit code của vitest
    - Teardown trong finally (drop cluster)
    - Từ chối service lạ và path traversal (../)
    - Không in URL / secrets
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Tái sử dụng disposable_postgres
from tests.e2e.stack.disposable_postgres import (
    apply_migrations,
    create_disposable_cluster,
    drop_disposable_cluster,
)
VALID_SERVICES = ("company", "cosa")


def validate_args(service: str, test_files: Sequence[str]) -> tuple[str, list[str]]:
    if service not in VALID_SERVICES:
        raise ValueError(f"unknown service '{service}', allowed: {', '.join(VALID_SERVICES)}")

    if not test_files:
        raise ValueError("no test files specified")

    service_dir = (REPO_ROOT / "services" / service).resolve()
    clean_files: list[str] = []

    for tf in test_files:
        if ".." in tf or tf.startswith("/"):
            raise ValueError(f"path traversal detected: '..' or absolute paths not allowed: '{tf}'")
        resolved = (service_dir / tf).resolve()
        try:
            resolved.relative_to(service_dir)
        except ValueError:
            raise ValueError(f"file outside service root: '{tf}'")
        clean_files.append(tf)

    return service, clean_files


def run_audit_tests(service: str, test_files: Sequence[str]) -> int:
    service, clean_files = validate_args(service, test_files)
    service_dir = REPO_ROOT / "services" / service

    cluster = create_disposable_cluster(secrets.token_hex(8))
    try:
        apply_migrations(cluster)
        child_env = dict(os.environ)
        child_env.update(
            WORKSPACE_DATABASE_URL=cluster.workspace_app_url,
            COSA_DATABASE_URL=cluster.cosa_app_url,
            AGENT_DATABASE_URL=cluster.agent_app_url,
        )
        result = subprocess.run(
            ["npx", "vitest", "run", *clean_files],
            cwd=service_dir,
            env=child_env,
            check=False,
        )
        return result.returncode
    finally:
        drop_disposable_cluster(cluster)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) < 2:
        print(
            "Usage: run_business_audit_tests.py <company|cosa> <vitest-file>...",
            file=sys.stderr,
        )
        return 1

    service = args[0]
    test_files = args[1:]

    try:
        return run_audit_tests(service, test_files)
    except Exception as exc:
        print(f"Error running business audit tests: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
