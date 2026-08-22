"""Reference device executor worker for Codex and Claude Code jobs."""

from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable


class SubprocessRunner:
    def run(self, argv, *, cwd, timeout, shell=False):
        return subprocess.run(
            argv,
            cwd=cwd,
            timeout=timeout,
            shell=shell,
            capture_output=True,
            text=True,
            check=False,
        )


@contextmanager
def isolated_git_worktree(repo_path: str):
    worktree = Path(tempfile.mkdtemp(prefix="cosa-device-worktree-"))
    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), "HEAD"],
            cwd=repo_path,
            shell=False,
            capture_output=True,
            text=True,
            check=True,
        )
        yield worktree
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=repo_path,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
        shutil.rmtree(worktree, ignore_errors=True)


def _argv(executor_kind: str, task: str) -> list[str]:
    if executor_kind == "codex":
        return ["codex", "exec", "--json", task]
    if executor_kind == "claude":
        return ["claude", "-p", task, "--output-format", "json"]
    raise ValueError(f"Unsupported device executor kind '{executor_kind}'")


def _excerpt(value: str, limit: int = 8000) -> str:
    # Enrollment and lease tokens are never passed into the process or output
    # payload, and excerpts are bounded before transport.
    return value[-limit:]


def run_once(
    http_client,
    runner,
    *,
    executor_kind: str,
    repo_path: str,
    worktree_factory: Callable = isolated_git_worktree,
) -> bool:
    claim = http_client.claim(executor_kind)
    if not claim:
        return False
    task = str((claim.get("request") or {}).get("task") or "")
    lease_token = claim["lease_token"]
    timeout = int((claim.get("request") or {}).get("timeout_seconds", 900))

    with worktree_factory(repo_path) as worktree:
        completed = runner.run(
            _argv(executor_kind, task),
            cwd=str(worktree),
            timeout=timeout,
            shell=False,
        )
        payload = {
            "status": "SUCCEEDED" if completed.returncode == 0 else "FAILED",
            "worktree_path": str(worktree),
            "test_results": {
                "exit_code": completed.returncode,
                "stdout_excerpt": _excerpt(completed.stdout or ""),
                "stderr_excerpt": _excerpt(completed.stderr or ""),
            },
        }
        http_client.submit(
            claim["job_id"],
            claim["workspace_id"],
            lease_token,
            payload,
        )
    return True


def main() -> None:
    raise SystemExit(
        "Configure an enrolled device HTTP client and call run_once; tokens "
        "must be supplied by a secret store, never command-line arguments."
    )


if __name__ == "__main__":
    main()
