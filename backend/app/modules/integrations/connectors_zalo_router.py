import base64
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.db.models import User, WorkspaceMember, MCPConnection

router = APIRouter()

_TIMEOUT = 180  # 3 phút hết hạn QR Zalo
_SESS_TTL = 900
_sessions: Dict[str, dict] = {}

_SUCCESS_EVENTS = {"login", "login_success", "success", "ready", "logged_in", "authenticated"}
_CLI_PACKAGE = "zalo-agent-cli@1.6.2"

def get_state_dir() -> str:
    base_dir = os.environ.get("JAVIS_STATE_DIR", os.path.expanduser("~/.javis"))
    path = os.path.join(base_dir, "connector-home")
    os.makedirs(path, exist_ok=True)
    return path

def _sweep():
    now = time.time()
    for sid in [k for k, v in _sessions.items() if now - v["ts"] > _SESS_TTL]:
        cancel_session(sid)
        _sessions.pop(sid, None)

def _npx_argv():
    npx = shutil.which("npx")
    if not npx:
        return None
    argv = [npx, "-y", _CLI_PACKAGE, "login", "--json"]
    if npx.lower().endswith((".cmd", ".bat")):
        argv = ["cmd.exe", "/c"] + argv
    return argv

def _qr_from_event(obj: dict, home: str) -> str:
    for k in ("dataUrl", "data_url", "image"):
        v = obj.get(k)
        if isinstance(v, str) and v.startswith("data:image"):
            return v
    f = obj.get("file")
    if isinstance(f, str) and os.path.isfile(f):
        try:
            return "data:image/png;base64," + base64.b64encode(open(f, "rb").read()).decode("ascii")
        except OSError:
            pass
    p = os.path.join(home, ".zalo-agent-cli", "qr.png")
    if os.path.isfile(p):
        try:
            return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode("ascii")
        except OSError:
            pass
    return ""

def _finish_ok(sess: dict, obj: dict, db: Session, workspace_id: str):
    label = (
        obj.get("displayName") or obj.get("display_name") or obj.get("name")
        or obj.get("ownId") or obj.get("own_id") or sess["label"] or "Tài khoản Zalo"
    )
    name = f"Zalo Agent ({str(label)[:40]})"
    
    # Kiểm tra xem kết nối đã tồn tại chưa
    existing = db.query(MCPConnection).filter(
        MCPConnection.workspace_id == workspace_id,
        MCPConnection.name == name
    ).first()
    
    config_data = {
        "home_dir": sess["home"],
        "own_id": obj.get("ownId") or obj.get("own_id") or "",
        "display_name": str(label)
    }
    
    if not existing:
        conn = MCPConnection(
            workspace_id=workspace_id,
            name=name,
            config_jsonb=config_data,
            status="connected"
        )
        db.add(conn)
    else:
        existing.config_jsonb = config_data
        existing.status = "connected"
        conn = existing
        
    db.commit()
    db.refresh(conn)
    sess.update(state="done", label=str(label)[:60], conn_id=str(conn.id))

def _reader(sid: str, db: Session, workspace_id: str):
    sess = _sessions.get(sid)
    if not sess:
        return
    proc = sess["proc"]
    got_qr = False
    try:
        for raw in iter(proc.stdout.readline, ""):
            if sess.get("state") in ("done", "error"):
                break
            raw = (raw or "").strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            ev = str(obj.get("event") or "").lower()
            if ev == "qr":
                qr = _qr_from_event(obj, sess["home"])
                if qr:
                    got_qr = True
                    sess.update(state="qr", qr=qr)
                continue
            if ev in _SUCCESS_EVENTS or (not ev and (obj.get("ownId") or obj.get("own_id"))):
                _finish_ok(sess, obj, db, workspace_id)
                break
            if ev in ("error", "failed"):
                sess.update(state="error", error=str(obj.get("message") or obj.get("error") or "Đăng nhập thất bại"))
                break
    except Exception as e:
        if sess.get("state") not in ("done", "error"):
            sess.update(state="error", error=f"{type(e).__name__}: {e}")
    finally:
        try:
            rc = proc.wait(timeout=5)
        except Exception:
            rc = None
        if sess.get("state") not in ("done", "error"):
            if rc == 0 and got_qr:
                _finish_ok(sess, {}, db, workspace_id)
            else:
                err_tail = ""
                try:
                    err_tail = (proc.stderr.read() or "")[-300:]
                except Exception:
                    pass
                sess.update(state="error", error="Đăng nhập Zalo chưa hoàn tất" + (f" (exit {rc}): {err_tail}" if rc else ""))

def cancel_session(sid: str):
    sess = _sessions.get(sid)
    if not sess:
        return
    try:
        if sess["proc"].poll() is None:
            sess["proc"].kill()
    except Exception:
        pass

class ZaloStartRequest(BaseModel):
    workspace_id: str
    label: Optional[str] = "Zalo Account"

@router.post("/zalo/start")
def start_zalo_qr(
    data: ZaloStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _sweep()
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == data.workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Tài khoản không thuộc workspace này")

    argv = _npx_argv()
    if not argv:
        raise HTTPException(status_code=400, detail="Cần cài đặt Node.js 20+ (lệnh npx) trên máy chủ để chạy Zalo Agent MCP")

    sid = uuid.uuid4().hex[:10]
    home = os.path.join(get_state_dir(), f"zalo-{data.workspace_id[:8]}-{sid[:6]}")
    os.makedirs(home, exist_ok=True)

    env = dict(os.environ)
    env["HOME"] = home
    env["USERPROFILE"] = home
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", env=env, **kwargs
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Không khởi chạy được npx zalo-agent-cli: {e}")

    _sessions[sid] = {
        "state": "starting",
        "qr": "",
        "label": data.label or "Zalo",
        "conn_id": "",
        "error": "",
        "proc": proc,
        "home": home,
        "ts": time.time(),
        "workspace_id": data.workspace_id
    }

    threading.Thread(target=_reader, args=(sid, db, data.workspace_id), daemon=True).start()
    return {"status": "success", "sid": sid}

@router.get("/zalo/status/{sid}")
def get_zalo_qr_status(
    sid: str,
    current_user: User = Depends(get_current_user)
):
    sess = _sessions.get(sid)
    if not sess:
        return {"state": "error", "error": "Phiên đăng nhập QR không tồn tại hoặc đã hết hạn"}
    return {
        "state": sess["state"],
        "qr": sess.get("qr", ""),
        "label": sess.get("label", ""),
        "conn_id": sess.get("conn_id", ""),
        "error": sess.get("error", "")
    }

@router.post("/zalo/cancel/{sid}")
def cancel_zalo_qr(
    sid: str,
    current_user: User = Depends(get_current_user)
):
    cancel_session(sid)
    _sessions.pop(sid, None)
    return {"status": "success", "message": "Đã hủy phiên quét mã QR Zalo"}
