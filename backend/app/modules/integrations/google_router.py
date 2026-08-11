"""Endpoint OAuth2 Google. Mount dưới /api/v1/connectors/google."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.integrations import google_oauth_service
from app.modules.integrations.google_connection_service import (
    connected_email,
    get_google_connection,
    has_usable_google_connection,
    store_connection,
)
from app.modules.integrations.google_oauth_service import GoogleOAuthError

logger = logging.getLogger(__name__)

router = APIRouter()


def _result_page(title: str, message: str, ok: bool) -> HTMLResponse:
    """Google trả người dùng về đây trong trình duyệt, không phải trong app - nên chỗ này
    phải tự nói được kết quả thay vì trả JSON trần."""
    color = "#22c55e" if ok else "#ef4444"
    return HTMLResponse(
        f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:-apple-system,Segoe UI,sans-serif;background:#0f172a;color:#e2e8f0;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
  <div style="max-width:480px;text-align:center;padding:32px">
    <div style="font-size:48px;color:{color}">{"✓" if ok else "✕"}</div>
    <h1 style="font-size:20px">{title}</h1>
    <p style="color:#94a3b8;line-height:1.6">{message}</p>
    <p style="color:#64748b;font-size:13px">Bạn có thể đóng cửa sổ này và quay lại COSA OS.</p>
  </div>
</body></html>""",
        status_code=200 if ok else 400,
    )


@router.get("/google/status")
def google_status(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Flutter poll endpoint này sau khi mở trình duyệt để biết khi nào kết nối xong."""
    connection = get_google_connection(db, workspace_id)
    usable = has_usable_google_connection(db, workspace_id)
    return {
        "server_configured": google_oauth_service.is_configured(),
        "connected": usable,
        "email": connected_email(db, workspace_id),
        # Bản ghi cũ tạo bằng luồng giả: có dòng nhưng không có token nào.
        "needs_reconnect": bool(connection and not usable),
    }


@router.post("/google/oauth/start")
def start_google_oauth(
    workspace_id: int,
    login_hint: str | None = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    try:
        state = google_oauth_service.sign_state(workspace_id, member.user_id)
        return {"authorize_url": google_oauth_service.build_authorize_url(state, login_hint)}
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/google/oauth/callback")
async def google_oauth_callback(
    state: str = "",
    code: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    """Google gọi vào đây trong trình duyệt của người dùng, KHÔNG kèm JWT của app.

    Vì thế quyền truy cập workspace được chứng minh bằng chữ ký trên ``state`` (ký lúc
    /oauth/start, khi còn có JWT), chứ không bằng header Authorization.
    """
    if error:
        return _result_page("Chưa kết nối được", f"Google báo: {error}", ok=False)

    try:
        payload = google_oauth_service.verify_state(state)
    except GoogleOAuthError as exc:
        return _result_page("Chưa kết nối được", str(exc), ok=False)

    if not code:
        return _result_page("Chưa kết nối được", "Google không trả về mã đăng nhập.", ok=False)

    try:
        tokens = await google_oauth_service.exchange_code(code)
        email = await google_oauth_service.fetch_email(tokens.get("access_token", ""))
    except GoogleOAuthError as exc:
        return _result_page("Chưa kết nối được", str(exc), ok=False)
    except Exception:
        logger.exception("Đổi code Google thất bại")
        return _result_page(
            "Chưa kết nối được", "Không liên lạc được với Google, thử lại sau.", ok=False
        )

    workspace_id = int(payload["workspace_id"])
    store_connection(db, workspace_id, email or "Gmail", tokens["refresh_token"])
    return _result_page(
        "Đã kết nối Gmail",
        f"Hòm thư <b>{email}</b> đã sẵn sàng. Giờ bạn có thể nhờ COSA OS đọc và tóm tắt email.",
        ok=True,
    )


@router.get("/google/oauth/callback/redirect")
def callback_redirect(url: str):
    """Chỗ móc sẵn cho bản web sau này (đưa người dùng về đúng trang trong app)."""
    return RedirectResponse(url)
