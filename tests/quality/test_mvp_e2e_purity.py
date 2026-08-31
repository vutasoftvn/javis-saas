import tempfile
from pathlib import Path

from scripts.check_mvp_e2e_purity import run_check


def test_mvp_e2e_purity_scanner_detects_prohibited_constructs():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Prohibited unittest.mock import
        f1 = tmp_path / "test_mvp_bad_mock.py"
        f1.write_text("import unittest.mock\n")

        # 2. Prohibited AsyncMock symbol import
        f2 = tmp_path / "test_mvp_bad_symbol.py"
        f2.write_text("from unittest.mock import AsyncMock\n")

        # 3. Prohibited pytest.mark.skip decorator
        f3 = tmp_path / "test_mvp_bad_skip.py"
        f3.write_text(
            "import pytest\n@pytest.mark.skip(reason='test')\ndef test_something(): pass\n"
        )

        # 4. Prohibited in-memory database string
        f4 = tmp_path / "test_mvp_bad_db.py"
        f4.write_text("db_url = 'sqlite:///:memory:'\n")

        # 5. Clean test
        f5 = tmp_path / "test_mvp_clean.py"
        f5.write_text("import httpx\ndef test_real(): assert 1 == 1\n")

        # 6. In-process transport and test doubles are integration-only.
        f6 = tmp_path / "test_mvp_bad_in_process.py"
        f6.write_text(
            "import httpx\n"
            "import pytest\n"
            "from agent.runs.repository import InMemoryRunRepository\n"
            "from agent_testkit.fake_sdk_model import FakeSDKModel\n"
            "from tests.apps.cosa.auth_test_helpers import override_authenticated_identity\n"
            "transport = httpx.ASGITransport(app=None)\n"
            "pytest.skip('missing stack')\n"
            "def test_monkeypatch(monkeypatch):\n"
            "    monkeypatch.setattr(httpx, 'Client', object)\n"
        )

        violations = run_check(tmp_path)
        assert len(violations) >= 11
        assert any("NO_MOCK_IMPORT" in v for v in violations)
        assert any("NO_MOCK_SYMBOL" in v for v in violations)
        assert any("NO_SKIPPED_TEST" in v for v in violations)
        assert any("NO_IN_MEMORY_DB" in v for v in violations)
        assert any("NO_IN_PROCESS_TRANSPORT" in v for v in violations)
        assert any("NO_TEST_DOUBLE" in v for v in violations)
        assert any("NO_TEST_IDENTITY_OVERRIDE" in v for v in violations)
        assert any("NO_MONKEYPATCH" in v for v in violations)
        assert sum("NO_SKIPPED_TEST" in v for v in violations) >= 2
        assert not any("test_mvp_clean.py" in v for v in violations)

        missing = run_check(tmp_path, required_files=frozenset({"test_mvp_required.py"}))
        assert any("MISSING_REQUIRED_MVP_TEST" in v for v in missing)
