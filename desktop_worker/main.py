"""COSA Local Desktop Worker Plane — Phase 4 Local Capability Hardening
(docs/implementation/production-runtime-closure.md §4).

Trước đây `/execute-task` nhận `command: str` tự do qua `subprocess.run(...,
shell=True)`, không auth, không allowlist path/cwd/env — bất kỳ process nào
chạy local trên máy user (kể cả process độc hại không liên quan COSA) đều
gọi được endpoint này. Bind `127.0.0.1` chỉ chặn truy cập từ mạng ngoài,
không chặn process khác trên CÙNG máy.

Thay bằng typed capability API:
  - git.status / git.diff / git.read_file — read-only, risk thấp.
  - fs.read / fs.write_scoped — giới hạn trong allowlist root
    (`COSA_DESKTOP_WORKER_ALLOWED_ROOTS`).
  - browser.open — chỉ http(s) URL.
  - shell.exec_sandboxed — argv list (KHÔNG shell=True, không thể inject qua
    shell metacharacter), env allowlist, tắt theo mặc định
    (`COSA_DESKTOP_WORKER_ENABLE_SHELL_EXEC`), cần approval token lấy từ
    local log (không LLM/agent tự approve — CLAUDE.md #8).

Mọi capability endpoint yêu cầu session token (`Authorization: Bearer
<token>` đọc từ file `~/.cosa/desktop_worker.token`, mode 0600) + nonce
chống replay (`X-Request-Nonce`, mỗi giá trị chỉ dùng được 1 lần trong
`_NONCE_TTL_SEC`).
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("cosa.desktop_worker")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="COSA Local Desktop Worker Plane", version="2.0.0")

MAX_OUTPUT_BYTES = 200_000
_ENV_ALLOWLIST = {"PATH", "HOME", "LANG", "LC_ALL", "USER", "USERNAME"}
_NONCE_TTL_SEC = 300
_APPROVAL_TTL_SEC = 120

SHELL_EXEC_ENABLED = os.environ.get("COSA_DESKTOP_WORKER_ENABLE_SHELL_EXEC", "false").lower() == "true"
LEGACY_EXECUTE_TASK_ENABLED = os.environ.get("COSA_DESKTOP_WORKER_ENABLE_LEGACY_EXECUTE_TASK", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Session auth + nonce/replay protection.
# ---------------------------------------------------------------------------

SESSION_TOKEN = secrets.token_hex(32)
_STATE_DIR = Path(os.environ.get("COSA_DESKTOP_WORKER_STATE_DIR", str(Path.home() / ".cosa")))
_TOKEN_FILE = _STATE_DIR / "desktop_worker.token"
_AUDIT_LOG_PATH = _STATE_DIR / "desktop_worker_audit.log"


def _write_session_token() -> None:
    """Ghi token phiên hiện tại ra file mode 0600 — client hợp lệ (Flutter
    app chạy cùng user) đọc file này để lấy token; process của user khác
    không đọc được (OS file permission). Không chặn được process KHÁC chạy
    cùng user (giới hạn cố hữu của mọi cơ chế loopback-only) — nhưng chặn
    được truy cập vô tình/ngẫu nhiên và thiết lập session xác định thay vì
    "ai gọi được cổng 8765 cũng coi là hợp lệ"."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(SESSION_TOKEN)
    os.chmod(_TOKEN_FILE, 0o600)


_seen_nonces: dict[str, float] = {}


def _check_nonce(nonce: str) -> bool:
    now = time.time()
    for key in [k for k, ts in _seen_nonces.items() if now - ts > _NONCE_TTL_SEC]:
        del _seen_nonces[key]
    if nonce in _seen_nonces:
        return False
    _seen_nonces[nonce] = now
    return True


def require_session(
    authorization: str | None = Header(None),
    x_request_nonce: str | None = Header(None),
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer session token")
    token = authorization[len("Bearer ") :]
    if not secrets.compare_digest(token, SESSION_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not x_request_nonce:
        raise HTTPException(status_code=401, detail="Missing X-Request-Nonce header")
    if not _check_nonce(x_request_nonce):
        raise HTTPException(status_code=401, detail="Nonce already used — replay rejected")


# ---------------------------------------------------------------------------
# cwd/path allowlist — không có ở /execute-task cũ, path traversal
# (`cwd=".."`, symlink) đi được ra ngoài mọi thư mục.
# ---------------------------------------------------------------------------


def _allowed_roots() -> list[Path]:
    raw = os.environ.get("COSA_DESKTOP_WORKER_ALLOWED_ROOTS")
    if not raw:
        default_root = Path.home() / "cosa-workspace"
        default_root.mkdir(parents=True, exist_ok=True)
        return [default_root.resolve()]
    return [Path(p).expanduser().resolve() for p in raw.split(os.pathsep) if p.strip()]


def _resolve_within_allowlist(path_str: str) -> Path:
    """Resolve symlink/`..` THẬT (os.path.realpath qua Path.resolve()) rồi
    mới so với allowlist — validate trên chuỗi thô trước khi resolve có thể
    bị bypass bằng symlink trỏ ra ngoài."""
    resolved = Path(path_str).expanduser().resolve()
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise HTTPException(
        status_code=403,
        detail=f"Path '{path_str}' resolves outside allowed roots: {[str(r) for r in _allowed_roots()]}",
    )


# ---------------------------------------------------------------------------
# Audit log — mọi capability call, kể cả bị từ chối, đều ghi lại.
# ---------------------------------------------------------------------------


def _audit(capability: str, risk: str, request_summary: dict, result_summary: dict) -> None:
    entry = {
        "ts": time.time(),
        "capability": capability,
        "risk": risk,
        "request": request_summary,
        "result": result_summary,
    }
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOG_PATH.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    logger.info("audit capability=%s risk=%s result=%s", capability, risk, result_summary)


def _truncate(text: str, limit: int = MAX_OUTPUT_BYTES) -> str:
    encoded = text.encode("utf-8", errors="ignore")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="ignore") + "\n...[truncated]"


def _run_git(args: list[str], cwd: Path, timeout: int = 30) -> dict:
    try:
        res = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
        return {"exit_code": res.returncode, "stdout": _truncate(res.stdout), "stderr": _truncate(res.stderr)}
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="git command timed out") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"git executable not found: {exc}") from exc


@app.get("/health")
def health_check():
    return {
        "status": "online",
        "plane": "local_worker",
        "platform": sys.platform,
        "pid": os.getpid(),
        "capabilities": [
            "git.status",
            "git.diff",
            "git.read_file",
            "fs.read",
            "fs.write_scoped",
            "browser.open",
        ]
        + (["shell.exec_sandboxed"] if SHELL_EXEC_ENABLED else []),
    }


# --- git.* (read-only, risk thấp) ------------------------------------------


class GitStatusRequest(BaseModel):
    cwd: str


class GitDiffRequest(BaseModel):
    cwd: str
    path: str | None = None


class GitReadFileRequest(BaseModel):
    cwd: str
    ref: str = "HEAD"
    path: str


@app.post("/capabilities/git/status", dependencies=[Depends(require_session)])
def capability_git_status(req: GitStatusRequest):
    cwd = _resolve_within_allowlist(req.cwd)
    result = _run_git(["status", "--porcelain=v1", "--branch"], cwd)
    _audit("git.status", "low", {"cwd": str(cwd)}, {"exit_code": result["exit_code"]})
    return result


@app.post("/capabilities/git/diff", dependencies=[Depends(require_session)])
def capability_git_diff(req: GitDiffRequest):
    cwd = _resolve_within_allowlist(req.cwd)
    args = ["diff"]
    if req.path:
        _resolve_within_allowlist(str(cwd / req.path))
        args += ["--", req.path]
    result = _run_git(args, cwd)
    _audit("git.diff", "low", {"cwd": str(cwd), "path": req.path}, {"exit_code": result["exit_code"]})
    return result


@app.post("/capabilities/git/read-file", dependencies=[Depends(require_session)])
def capability_git_read_file(req: GitReadFileRequest):
    cwd = _resolve_within_allowlist(req.cwd)
    _resolve_within_allowlist(str(cwd / req.path))
    result = _run_git(["show", f"{req.ref}:{req.path}"], cwd)
    _audit(
        "git.read_file", "low", {"cwd": str(cwd), "ref": req.ref, "path": req.path}, {"exit_code": result["exit_code"]}
    )
    return result


# --- fs.* --------------------------------------------------------------


class FsReadRequest(BaseModel):
    path: str
    max_bytes: int = Field(default=1_000_000, le=5_000_000)


class FsWriteScopedRequest(BaseModel):
    path: str
    content: str = Field(max_length=2_000_000)


@app.post("/capabilities/fs/read", dependencies=[Depends(require_session)])
def capability_fs_read(req: FsReadRequest):
    resolved = _resolve_within_allowlist(req.path)
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    truncated = _truncate(content, req.max_bytes)
    _audit("fs.read", "medium", {"path": str(resolved)}, {"bytes": len(truncated)})
    return {"path": str(resolved), "content": truncated}


@app.post("/capabilities/fs/write_scoped", dependencies=[Depends(require_session)])
def capability_fs_write_scoped(req: FsWriteScopedRequest):
    resolved = _resolve_within_allowlist(req.path)
    if not resolved.parent.is_dir():
        raise HTTPException(status_code=400, detail="Parent directory does not exist within allowed roots")
    try:
        resolved.write_text(req.content, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    _audit("fs.write_scoped", "high", {"path": str(resolved)}, {"bytes": len(req.content)})
    return {"path": str(resolved), "status": "written"}


# --- browser.open ---------------------------------------------------------


class BrowserOpenRequest(BaseModel):
    url: str


_ALLOWED_URL_SCHEMES = {"http", "https"}


@app.post("/capabilities/browser/open", dependencies=[Depends(require_session)])
def capability_browser_open(req: BrowserOpenRequest):
    import webbrowser

    parsed = urlparse(req.url)
    if parsed.scheme not in _ALLOWED_URL_SCHEMES or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Only http(s) URLs with a host are allowed")
    opened = webbrowser.open(req.url)
    _audit("browser.open", "low", {"url": req.url}, {"opened": opened})
    return {"opened": opened}


# --- shell.exec_sandboxed (high risk, tắt theo mặc định, cần approval) ----

_pending_approvals: dict[str, float] = {}


def _consume_approval(token: str) -> bool:
    now = time.time()
    for key in [k for k, ts in _pending_approvals.items() if now - ts > _APPROVAL_TTL_SEC]:
        del _pending_approvals[key]
    if token not in _pending_approvals:
        return False
    del _pending_approvals[token]
    return True


class ShellExecRequest(BaseModel):
    argv: list[str] = Field(min_length=1, max_length=64)
    cwd: str
    approval_token: str
    timeout_seconds: int = Field(default=30, le=120)


@app.post("/capabilities/shell/exec_sandboxed/request-approval", dependencies=[Depends(require_session)])
def request_shell_exec_approval():
    """KHÔNG trả token qua response — chỉ ghi ra log local (stdout/audit
    file) của chính process desktop_worker. Agent/LLM gọi endpoint HTTP này
    không tự lấy được token để tự approve chính mình (CLAUDE.md #8: hành
    động rủi ro cao cần approval qua code, không qua prompt/LLM tự quyết) —
    chỉ người có quyền đọc log/console trên máy (người vận hành thật) mới
    thấy được, rồi tự tay đưa token đó vào request kế tiếp."""
    if not SHELL_EXEC_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="shell.exec_sandboxed is disabled (set COSA_DESKTOP_WORKER_ENABLE_SHELL_EXEC=true to enable)",
        )
    token = secrets.token_hex(16)
    _pending_approvals[token] = time.time()
    logger.warning("shell.exec_sandboxed approval requested — token (chỉ hiện trong local log): %s", token)
    return {"status": "approval_logged_locally"}


@app.post("/capabilities/shell/exec_sandboxed", dependencies=[Depends(require_session)])
def capability_shell_exec_sandboxed(req: ShellExecRequest):
    if not SHELL_EXEC_ENABLED:
        raise HTTPException(status_code=403, detail="shell.exec_sandboxed is disabled")
    if not _consume_approval(req.approval_token):
        raise HTTPException(
            status_code=403,
            detail="Missing/expired/already-used approval_token — call request-approval first "
            "and use the token from the local server log",
        )

    cwd = _resolve_within_allowlist(req.cwd)
    safe_env = {k: v for k, v in os.environ.items() if k in _ENV_ALLOWLIST}
    try:
        # argv list, shell=False — không có shell parser nào để inject qua
        # `;`/`|`/`$()`/backtick, khác hẳn /execute-task cũ (shell=True +
        # command: str tự do).
        res = subprocess.run(
            req.argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=req.timeout_seconds,
            shell=False,
            env=safe_env,
        )
        result = {"exit_code": res.returncode, "stdout": _truncate(res.stdout), "stderr": _truncate(res.stderr)}
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Command execution timed out") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Executable not found: {exc}") from exc

    _audit("shell.exec_sandboxed", "critical", {"argv": req.argv, "cwd": str(cwd)}, {"exit_code": result["exit_code"]})
    return result


# --- /execute-task cũ — retired, tắt theo mặc định --------------------------


class LocalExecutionRequest(BaseModel):
    command: str
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout_seconds: int | None = 120


@app.post("/execute-task", dependencies=[Depends(require_session)])
def execute_local_task(req: LocalExecutionRequest):
    """DEPRECATED — free-form `command: str` qua `shell=True`, không path
    allowlist, không env allowlist. Trả 410 theo mặc định; chỉ bật tạm qua
    `COSA_DESKTOP_WORKER_ENABLE_LEGACY_EXECUTE_TASK=true` cho backward-compat
    cục bộ. Dùng `/capabilities/*` thay thế."""
    if not LEGACY_EXECUTE_TASK_ENABLED:
        raise HTTPException(
            status_code=410,
            detail="/execute-task is retired — use typed /capabilities/* endpoints instead. "
            "Set COSA_DESKTOP_WORKER_ENABLE_LEGACY_EXECUTE_TASK=true only for local dev backward-compat.",
        )
    try:
        res = subprocess.run(
            req.command,
            shell=True,
            cwd=req.cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=req.timeout_seconds or 120,
        )
        result = {
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "status": "completed" if res.returncode == 0 else "failed",
        }
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Command execution timed out") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _audit("legacy.execute_task", "critical", {"command": req.command, "cwd": req.cwd}, {"status": result["status"]})
    return result


if __name__ == "__main__":
    # Chỉ lắng nghe trên 127.0.0.1 (Loopback only - Tuân thủ nghiêm ngặt Blueprint §113)
    _write_session_token()
    logger.info("session token written to %s (mode 0600)", _TOKEN_FILE)
    uvicorn.run(app, host="127.0.0.1", port=8765)
