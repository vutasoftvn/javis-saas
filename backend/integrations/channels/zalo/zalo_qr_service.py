"""Durable, workspace-scoped Zalo QR login jobs run exclusively by agent-worker."""

import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MCPConnection, ZaloQrSession
from db.session import SessionLocal

QR_TIMEOUT_SECONDS = 180
CLI_PACKAGE = "zalo-agent-cli@1.6.2"
SUCCESS_EVENTS = {"login", "login_success", "success", "ready", "logged_in", "authenticated"}


def create_qr_session(db: Session, workspace_id: int, user_id: int) -> ZaloQrSession:
    session = ZaloQrSession(
        workspace_id=workspace_id,
        created_by_user_id=user_id,
        state="queued",
        expires_at=datetime.utcnow() + timedelta(seconds=QR_TIMEOUT_SECONDS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_qr_session_for_owner(db: Session, session_id: int, workspace_id: int, user_id: int) -> ZaloQrSession | None:
    return db.scalar(
        select(ZaloQrSession).where(
            ZaloQrSession.id == session_id,
            ZaloQrSession.workspace_id == workspace_id,
            ZaloQrSession.created_by_user_id == user_id,
        )
    )


def cancel_qr_session(db: Session, session: ZaloQrSession) -> None:
    if session.state not in {"done", "error", "cancelled", "expired"}:
        session.state = "cancelled"
        db.commit()


def _state_dir() -> str:
    root = os.environ.get("JAVIS_STATE_DIR", "/var/lib/javis-connectors")
    os.makedirs(root, exist_ok=True)
    return root


def _npx_argv() -> list[str] | None:
    npx = shutil.which("npx")
    return [npx, "-y", CLI_PACKAGE, "login", "--json"] if npx else None


def _update_session(session_id: int, **values: object) -> ZaloQrSession | None:
    db = SessionLocal()
    try:
        session = db.get(ZaloQrSession, session_id)
        if not session:
            return None
        for key, value in values.items():
            setattr(session, key, value)
        db.commit()
        db.refresh(session)
        return session
    finally:
        db.close()


def _qr_from_event(event: dict, home: str) -> str:
    for key in ("dataUrl", "data_url", "image"):
        value = event.get(key)
        if isinstance(value, str) and value.startswith("data:image"):
            return value
    candidate = event.get("file") or os.path.join(home, ".zalo-agent-cli", "qr.png")
    if isinstance(candidate, str) and os.path.isfile(candidate):
        try:
            with open(candidate, "rb") as image:
                return "data:image/png;base64," + base64.b64encode(image.read()).decode("ascii")
        except OSError:
            pass
    return ""


def _connect(session_id: int, event: dict, home: str) -> None:
    db = SessionLocal()
    try:
        qr_session = db.get(ZaloQrSession, session_id)
        if not qr_session or qr_session.state == "cancelled":
            return
        label = str(event.get("displayName") or event.get("display_name") or event.get("name") or event.get("ownId") or "Zalo")
        name = f"Zalo Agent ({label[:40]})"
        connection = db.scalar(select(MCPConnection).where(
            MCPConnection.workspace_id == qr_session.workspace_id,
            MCPConnection.name == name,
        ))
        config = {"home_dir": home, "own_id": event.get("ownId") or event.get("own_id") or "", "display_name": label}
        if connection is None:
            connection = MCPConnection(workspace_id=qr_session.workspace_id, name=name, config_jsonb=config, status="connected")
            db.add(connection)
            db.flush()
        else:
            connection.config_jsonb = config
            connection.status = "connected"
        qr_session.connection_id = connection.id
        qr_session.state = "done"
        qr_session.error = None
        db.commit()
    finally:
        db.close()


def process_one_queued_qr_session() -> bool:
    """Claim and process one job.  This must only be called by agent-worker."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        db.query(ZaloQrSession).filter(
            ZaloQrSession.state.in_(["queued", "starting", "qr"]),
            ZaloQrSession.expires_at <= now,
        ).update({"state": "expired"}, synchronize_session=False)
        job = db.scalar(select(ZaloQrSession).where(
            ZaloQrSession.state == "queued", ZaloQrSession.expires_at > now,
        ).with_for_update(skip_locked=True).limit(1))
        if job is None:
            db.commit()
            return False
        job.state = "starting"
        job.claimed_at = now
        session_id = job.id
        workspace_id = job.workspace_id
        db.commit()
    finally:
        db.close()

    argv = _npx_argv()
    if not argv:
        _update_session(session_id, state="error", error="Node.js 20+ (npx) không có trong agent-worker")
        return True

    home = os.path.join(_state_dir(), f"zalo-{workspace_id}-{session_id}")
    os.makedirs(home, exist_ok=True)
    env = dict(os.environ, HOME=home, USERPROFILE=home)
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   text=True, encoding="utf-8", errors="replace", env=env)
    except OSError as exc:
        _update_session(session_id, state="error", error=f"Không khởi chạy được Zalo Agent: {exc}")
        return True

    completed = False
    try:
        for raw in iter(process.stdout.readline, ""):
            current = _update_session(session_id)
            if current is None or current.state == "cancelled":
                process.kill()
                break
            if current.expires_at <= datetime.utcnow():
                _update_session(session_id, state="expired")
                process.kill()
                break
            try:
                event = json.loads(raw.strip())
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            kind = str(event.get("event") or "").lower()
            if kind == "qr":
                qr = _qr_from_event(event, home)
                if qr:
                    _update_session(session_id, state="qr", qr_data_url=qr)
            elif kind in SUCCESS_EVENTS or (not kind and (event.get("ownId") or event.get("own_id"))):
                _connect(session_id, event, home)
                completed = True
                break
            elif kind in {"error", "failed"}:
                _update_session(session_id, state="error", error=str(event.get("message") or event.get("error") or "Đăng nhập thất bại"))
                break
    except Exception as exc:
        _update_session(session_id, state="error", error=f"{type(exc).__name__}: {exc}")
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
    if not completed:
        db = SessionLocal()
        try:
            current = db.get(ZaloQrSession, session_id)
            if current and current.state in {"starting", "qr"}:
                current.state = "error"
                current.error = "Đăng nhập Zalo chưa hoàn tất"
                db.commit()
        finally:
            db.close()
    return True
