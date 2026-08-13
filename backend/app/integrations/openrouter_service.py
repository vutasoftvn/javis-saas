import os
import logging
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from app.modules.chat.model_registry import is_provider_configured

logger = logging.getLogger(__name__)

OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"


def _get_openrouter_api_key(workspace_id: Optional[int] = None) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key

    # Tra cứu khoá mã hoá từ WorkspaceSecret trong Postgres DB
    try:
        from app.db.session import SessionLocal
        from app.modules.integrations.models import WorkspaceSecret
        from app.modules.integrations.secrets_service import decrypt_for_workspace

        db = SessionLocal()
        try:
            query = db.query(WorkspaceSecret).filter(WorkspaceSecret.key == "openrouter")
            if workspace_id:
                query = query.filter(WorkspaceSecret.workspace_id == workspace_id)
            ws_secret = query.first()
            if ws_secret and ws_secret.encrypted_value:
                decrypted = decrypt_for_workspace(ws_secret.workspace_id, ws_secret.encrypted_value)
                if decrypted:
                    return decrypted
        finally:
            db.close()
    except Exception as e:
        logger.warning("Không thể lấy khoá OpenRouter từ WorkspaceSecret: %s", e)

    return ""


def fetch_openrouter_key_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Gọi OpenRouter API (GET /api/v1/key và GET /api/v1/credits) để lấy thông tin tài khoản, hạn mức và số dư thực tế.
    
    Nếu provider đã được cấu hình (qua env hoặc cờ PROVIDER_CONFIGURED_OPENROUTER), trả về configured: True.
    """
    if api_key == "":
        return {
            "configured": False,
            "label": None,
            "limit": None,
            "limit_remaining": None,
            "usage": None,
            "key_usage": None,
            "usage_daily": None,
            "usage_weekly": None,
            "usage_monthly": None,
            "account_usage": None,
            "balance": None,
            "total_credits": None,
            "is_free_tier": None,
        }

    key = api_key or _get_openrouter_api_key()
    is_conf = (is_provider_configured("openrouter") or bool(key)) and bool(key)

    if not is_conf or not key:
        return {
            "configured": False,
            "label": None,
            "limit": None,
            "limit_remaining": None,
            "usage": None,
            "key_usage": None,
            "usage_daily": None,
            "usage_weekly": None,
            "usage_monthly": None,
            "account_usage": None,
            "balance": None,
            "total_credits": None,
            "is_free_tier": None,
        }


    res = {
        "configured": True,
        "label": "OpenRouter Gateway",
        "limit": None,
        "limit_remaining": None,
        "usage": None,
        "key_usage": None,
        "usage_daily": None,
        "usage_weekly": None,
        "usage_monthly": None,
        "account_usage": None,
        "balance": None,
        "total_credits": None,
        "is_free_tier": None,
    }

    if key:
        headers = {"Authorization": f"Bearer {key}"}
        try:
            with httpx.Client(timeout=10.0) as client:

                try:
                    resp = client.get(OPENROUTER_KEY_URL, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        res["label"] = data.get("label") or "OpenRouter Key"
                        res["limit"] = data.get("limit")
                        res["limit_remaining"] = data.get("limit_remaining")
                        res["key_usage"] = data.get("usage")
                        res["usage"] = data.get("usage")
                        res["usage_daily"] = data.get("usage_daily")
                        res["usage_weekly"] = data.get("usage_weekly")
                        res["usage_monthly"] = data.get("usage_monthly")
                        res["is_free_tier"] = data.get("is_free_tier")
                except Exception as e:
                    logger.warning("Không thể lấy /v1/key từ OpenRouter: %s", e)

                try:
                    cred_resp = client.get("https://openrouter.ai/api/v1/credits", headers=headers)
                    if cred_resp.status_code == 200:
                        cdata = cred_resp.json().get("data", {})
                        total_credits = cdata.get("total_credits")
                        account_usage = cdata.get("total_usage")
                        res["total_credits"] = total_credits
                        res["account_usage"] = account_usage
                        if total_credits is not None and account_usage is not None:
                            calc_balance = max(0.0, float(total_credits) - float(account_usage))
                            res["balance"] = calc_balance
                            if res["limit_remaining"] is None:
                                res["limit_remaining"] = calc_balance
                except Exception as e:
                    logger.warning("Không thể lấy /v1/credits từ OpenRouter: %s", e)
        except Exception as e:
            logger.warning("Không thể lấy thông tin OpenRouter key/credits info: %s", e)

    return res





