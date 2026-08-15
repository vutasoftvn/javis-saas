import os
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.modules.integrations.email_providers.base import EmailProvider
from app.modules.integrations.secrets_service import decrypt_for_workspace

logger = logging.getLogger(__name__)


class ResendError(Exception):
    pass


class ResendEmailProvider(EmailProvider):
    """Resend email provider implementation using Resend REST API."""

    BASE_URL = "https://api.resend.com"

    def __init__(self, api_key: str, default_from: Optional[str] = None):
        if not api_key:
            raise ValueError("Resend API key is required")
        self.api_key = api_key
        self.default_from = default_from or os.environ.get("RESEND_DEFAULT_FROM", "COSA Growth <onboarding@resend.dev>")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/emails"
        sender = from_email or self.default_from

        payload: Dict[str, Any] = {
            "from": sender,
            "to": [to_email] if isinstance(to_email, str) else to_email,
            "subject": subject,
            "html": body_html,
        }
        if body_text:
            payload["text"] = body_text
        if reply_to:
            payload["reply_to"] = reply_to
        if tags:
            payload["tags"] = tags
        if headers:
            payload["headers"] = headers

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            if response.status_code >= 400:
                err_msg = response.text
                logger.error(f"Resend API error [{response.status_code}]: {err_msg}")
                raise ResendError(f"Resend send failed ({response.status_code}): {err_msg}")
            
            data = response.json()
            return {
                "success": True,
                "id": data.get("id"),
                "from": sender,
                "to": to_email,
            }

    async def send_template(
        self,
        to_email: str,
        template_id: str,
        template_data: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        # For Resend, templates can be rendered or sent with tags
        return await self.send_email(
            to_email=to_email,
            subject=f"Template {template_id}",
            body_html=f"<p>Templated content: {template_data or {}}</p>",
            from_email=from_email,
            tags=[{"name": "template_id", "value": template_id}],
        )

    async def verify_configuration(self) -> bool:
        """Verify API key validity via Resend API."""
        url = f"{self.BASE_URL}/api-keys"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._get_headers())
            return response.status_code == 200


def build_resend_client(db: Session, workspace_id: int) -> ResendEmailProvider:
    """
    Factory to construct ResendEmailProvider by resolving workspace secret or env fallback.
    """
    api_key = decrypt_for_workspace(db, workspace_id, "resend")
    if not api_key:
        api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise ResendError("Chưa cấu hình API Key cho Resend trong Workspace")

    return ResendEmailProvider(api_key=api_key)
