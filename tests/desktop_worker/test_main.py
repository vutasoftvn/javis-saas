"""Test cho desktop_worker/main.py — Phase 4 Local Capability Hardening
(docs/implementation/production-runtime-closure.md §4). Exit criteria:
path traversal test fail closed; shell metacharacter injection không áp
dụng được cho typed capability; unauthorized local process không gọi
capability host thành công."""
from __future__ import annotations

import importlib
import os
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def worker_module(tmp_path, monkeypatch):
    """Reload module với COSA_DESKTOP_WORKER_ALLOWED_ROOTS/STATE_DIR trỏ vào
    tmp_path — cô lập hoàn toàn khỏi filesystem thật của máy chạy test."""
    allowed_root = tmp_path / "workspace"
    allowed_root.mkdir()
    state_dir = tmp_path / "state"

    monkeypatch.setenv("COSA_DESKTOP_WORKER_ALLOWED_ROOTS", str(allowed_root))
    monkeypatch.setenv("COSA_DESKTOP_WORKER_STATE_DIR", str(state_dir))
    monkeypatch.delenv("COSA_DESKTOP_WORKER_ENABLE_SHELL_EXEC", raising=False)
    monkeypatch.delenv("COSA_DESKTOP_WORKER_ENABLE_LEGACY_EXECUTE_TASK", raising=False)

    import desktop_worker.main as m

    importlib.reload(m)
    m._allowed_root = allowed_root  # type: ignore[attr-defined]
    return m


@pytest.fixture()
def client(worker_module):
    return TestClient(worker_module.app)


def _auth_headers(worker_module) -> dict:
    return {
        "Authorization": f"Bearer {worker_module.SESSION_TOKEN}",
        "X-Request-Nonce": uuid.uuid4().hex,
    }


class TestHealthIsPublic:
    def test_health_check_no_auth_required(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "online"
        assert "shell.exec_sandboxed" not in res.json()["capabilities"]  # tắt theo mặc định


class TestUnauthorizedAccessRejected:
    """Exit criteria: unauthorized local process không gọi capability host thành công."""

    def test_missing_authorization_header_rejected(self, client, worker_module):
        res = client.post(
            "/capabilities/git/status",
            json={"cwd": str(worker_module._allowed_root)},
            headers={"X-Request-Nonce": uuid.uuid4().hex},
        )
        assert res.status_code == 401

    def test_wrong_token_rejected(self, client, worker_module):
        res = client.post(
            "/capabilities/git/status",
            json={"cwd": str(worker_module._allowed_root)},
            headers={"Authorization": "Bearer wrong-token", "X-Request-Nonce": uuid.uuid4().hex},
        )
        assert res.status_code == 401

    def test_missing_nonce_rejected(self, client, worker_module):
        res = client.post(
            "/capabilities/git/status",
            json={"cwd": str(worker_module._allowed_root)},
            headers={"Authorization": f"Bearer {worker_module.SESSION_TOKEN}"},
        )
        assert res.status_code == 401

    def test_replayed_nonce_rejected(self, client, worker_module):
        headers = {
            "Authorization": f"Bearer {worker_module.SESSION_TOKEN}",
            "X-Request-Nonce": "fixed-nonce-value",
        }
        first = client.post("/capabilities/git/status", json={"cwd": str(worker_module._allowed_root)}, headers=headers)
        assert first.status_code == 200

        replay = client.post("/capabilities/git/status", json={"cwd": str(worker_module._allowed_root)}, headers=headers)
        assert replay.status_code == 401
        assert "replay" in replay.json()["detail"].lower()

    def test_legacy_execute_task_disabled_by_default(self, client, worker_module):
        res = client.post(
            "/execute-task",
            json={"command": "echo hi"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 410


class TestPathTraversalFailsClosed:
    """Exit criteria: path traversal test fail closed."""

    def test_fs_read_outside_allowlist_rejected(self, client, worker_module):
        res = client.post(
            "/capabilities/fs/read",
            json={"path": "/etc/passwd"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 403

    def test_fs_read_relative_dotdot_traversal_rejected(self, client, worker_module):
        outside = worker_module._allowed_root / ".." / ".." / "etc" / "passwd"
        res = client.post(
            "/capabilities/fs/read",
            json={"path": str(outside)},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 403

    def test_fs_write_scoped_outside_allowlist_rejected(self, client, worker_module):
        res = client.post(
            "/capabilities/fs/write_scoped",
            json={"path": "/tmp/should_not_write_here.txt", "content": "pwned"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 403

    def test_fs_write_scoped_inside_allowlist_succeeds(self, client, worker_module):
        target = worker_module._allowed_root / "notes.txt"
        res = client.post(
            "/capabilities/fs/write_scoped",
            json={"path": str(target), "content": "hello"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 200
        assert target.read_text() == "hello"

    def test_fs_read_inside_allowlist_succeeds(self, client, worker_module):
        target = worker_module._allowed_root / "notes.txt"
        target.write_text("hello world")
        res = client.post(
            "/capabilities/fs/read",
            json={"path": str(target)},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 200
        assert res.json()["content"] == "hello world"

    def test_git_diff_path_escape_rejected(self, client, worker_module):
        res = client.post(
            "/capabilities/git/diff",
            json={"cwd": str(worker_module._allowed_root), "path": "../../../etc/passwd"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 403


class TestShellMetacharacterInjectionNotApplicable:
    """Exit criteria: shell metacharacter injection không áp dụng được cho
    typed capability — argv list + shell=False nghĩa là `;`/`|`/`$()`/backtick
    chỉ là literal argument, không có shell nào parse chúng."""

    def test_shell_exec_disabled_by_default(self, client, worker_module):
        res = client.post(
            "/capabilities/shell/exec_sandboxed",
            json={"argv": ["echo", "hi"], "cwd": str(worker_module._allowed_root), "approval_token": "x"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 403

    def test_shell_exec_enabled_requires_approval_token(self, client, worker_module, monkeypatch):
        monkeypatch.setattr(worker_module, "SHELL_EXEC_ENABLED", True)
        res = client.post(
            "/capabilities/shell/exec_sandboxed",
            json={"argv": ["echo", "hi"], "cwd": str(worker_module._allowed_root), "approval_token": "not-a-real-token"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 403
        assert "approval" in res.json()["detail"].lower()

    def test_shell_exec_metacharacters_treated_as_literal_argv_not_shell_syntax(self, client, worker_module, monkeypatch):
        monkeypatch.setattr(worker_module, "SHELL_EXEC_ENABLED", True)

        approval_res = client.post(
            "/capabilities/shell/exec_sandboxed/request-approval", headers=_auth_headers(worker_module)
        )
        assert approval_res.status_code == 200
        token = next(iter(worker_module._pending_approvals.keys()))

        marker_file = worker_module._allowed_root / "should_not_exist.txt"
        # Nếu đây bị hiểu như shell command, `; touch ...` sẽ tạo marker_file.
        # Với argv=["echo", "hi; touch ..."] thì toàn bộ chuỗi là 1 argument
        # literal truyền cho `echo`, không có gì thực thi `touch`.
        injection_payload = f"hi; touch {marker_file}; echo done"
        res = client.post(
            "/capabilities/shell/exec_sandboxed",
            json={
                "argv": ["echo", injection_payload],
                "cwd": str(worker_module._allowed_root),
                "approval_token": token,
            },
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["stdout"].strip() == injection_payload  # in nguyên văn, không bị shell tách lệnh
        assert not marker_file.exists()  # touch KHÔNG được thực thi

    def test_shell_exec_approval_token_single_use(self, client, worker_module, monkeypatch):
        monkeypatch.setattr(worker_module, "SHELL_EXEC_ENABLED", True)
        client.post("/capabilities/shell/exec_sandboxed/request-approval", headers=_auth_headers(worker_module))
        token = next(iter(worker_module._pending_approvals.keys()))

        first = client.post(
            "/capabilities/shell/exec_sandboxed",
            json={"argv": ["echo", "hi"], "cwd": str(worker_module._allowed_root), "approval_token": token},
            headers=_auth_headers(worker_module),
        )
        assert first.status_code == 200

        second = client.post(
            "/capabilities/shell/exec_sandboxed",
            json={"argv": ["echo", "hi"], "cwd": str(worker_module._allowed_root), "approval_token": token},
            headers=_auth_headers(worker_module),
        )
        assert second.status_code == 403  # token đã dùng, không reuse được

    def test_shell_exec_approval_endpoint_does_not_return_token_in_response(self, client, worker_module, monkeypatch):
        """Agent/LLM gọi HTTP endpoint này không tự lấy được token để tự
        approve chính mình — token chỉ nằm trong log/state nội bộ process."""
        monkeypatch.setattr(worker_module, "SHELL_EXEC_ENABLED", True)
        res = client.post(
            "/capabilities/shell/exec_sandboxed/request-approval", headers=_auth_headers(worker_module)
        )
        assert res.status_code == 200
        body_text = res.text
        for token in worker_module._pending_approvals.keys():
            assert token not in body_text


class TestBrowserOpenSchemeValidation:
    def test_rejects_non_http_scheme(self, client, worker_module):
        res = client.post(
            "/capabilities/browser/open",
            json={"url": "file:///etc/passwd"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 400

    def test_rejects_javascript_scheme(self, client, worker_module):
        res = client.post(
            "/capabilities/browser/open",
            json={"url": "javascript:alert(1)"},
            headers=_auth_headers(worker_module),
        )
        assert res.status_code == 400
