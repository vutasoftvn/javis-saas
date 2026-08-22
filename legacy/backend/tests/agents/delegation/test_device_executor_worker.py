from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


class FakeHttp:
    def __init__(self):
        self.submissions = []

    def claim(self, executor_kind):
        return {
            "job_id": "job-1",
            "workspace_id": "workspace-1",
            "lease_token": "secret-lease",
            "request": {"task": "Fix the failing test"},
        }

    def submit(self, job_id, workspace_id, lease_token, payload):
        self.submissions.append((job_id, workspace_id, lease_token, payload))


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, argv, *, cwd, timeout, shell):
        self.calls.append(
            SimpleNamespace(argv=argv, cwd=cwd, timeout=timeout, shell=shell)
        )
        return SimpleNamespace(returncode=0, stdout="done", stderr="")


@contextmanager
def fake_worktree(_repo_path):
    yield Path("/tmp/isolated-device-worktree")


def test_reference_worker_invokes_codex_with_argv_and_no_shell():
    from scripts.device_executor_worker import run_once

    http = FakeHttp()
    runner = FakeRunner()
    assert run_once(
        http,
        runner,
        executor_kind="codex",
        repo_path="/repo",
        worktree_factory=fake_worktree,
    ) is True

    assert runner.calls[0].shell is False
    assert runner.calls[0].argv[0] == "codex"
    assert http.submissions[0][2] == "secret-lease"
