from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import main / run_tests from scripts.run_business_audit_tests
from scripts.run_business_audit_tests import run_audit_tests, main, validate_args


def test_validate_args_rejects_unknown_service() -> None:
    with pytest.raises(ValueError, match="unknown service"):
        validate_args("unknown_svc", ["test.ts"])


def test_validate_args_rejects_directory_traversal() -> None:
    with pytest.raises(ValueError, match="path traversal"):
        validate_args("company", ["../../etc/passwd"])

    with pytest.raises(ValueError, match="path traversal"):
        validate_args("company", ["identity/tests/../secret.ts"])


def test_validate_args_accepts_valid_service_and_files() -> None:
    service, files = validate_args("company", ["operations/tests/okr-scoring.test.ts"])
    assert service == "company"
    assert files == ["operations/tests/okr-scoring.test.ts"]


def test_runner_teardown_on_nonzero_exit() -> None:
    mock_cluster = MagicMock()
    mock_cluster.workspace_app_url = "postgresql://mock_ws"
    mock_cluster.cosa_app_url = "postgresql://mock_cosa"
    mock_cluster.agent_app_url = "postgresql://mock_agent"

    with patch("scripts.run_business_audit_tests.create_disposable_cluster", return_value=mock_cluster) as mock_create, \
         patch("scripts.run_business_audit_tests.apply_migrations") as mock_apply, \
         patch("scripts.run_business_audit_tests.drop_disposable_cluster") as mock_drop, \
         patch("subprocess.run") as mock_subproc:

        mock_subproc.return_value = MagicMock(returncode=42)

        exit_code = run_audit_tests("company", ["operations/tests/okr-scoring.test.ts"])

        assert exit_code == 42
        mock_create.assert_called_once()
        mock_apply.assert_called_once_with(mock_cluster)
        mock_drop.assert_called_once_with(mock_cluster)

        # Check subprocess environment contains disposable URLs
        called_kwargs = mock_subproc.call_args[1]
        env = called_kwargs["env"]
        assert env["WORKSPACE_DATABASE_URL"] == "postgresql://mock_ws"
        assert env["COSA_DATABASE_URL"] == "postgresql://mock_cosa"
        assert env["AGENT_DATABASE_URL"] == "postgresql://mock_agent"


def test_runner_teardown_on_exception() -> None:
    mock_cluster = MagicMock()
    with patch("scripts.run_business_audit_tests.create_disposable_cluster", return_value=mock_cluster), \
         patch("scripts.run_business_audit_tests.apply_migrations", side_effect=RuntimeError("migrate boom")), \
         patch("scripts.run_business_audit_tests.drop_disposable_cluster") as mock_drop:

        with pytest.raises(RuntimeError, match="migrate boom"):
            run_audit_tests("company", ["operations/tests/okr-scoring.test.ts"])

        mock_drop.assert_called_once_with(mock_cluster)
