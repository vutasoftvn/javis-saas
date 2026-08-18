from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EmailProvider(ABC):
    """Abstract Base Class for email delivery providers."""

    @abstractmethod
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
        """Send a single email message."""
        pass

    @abstractmethod
    async def send_template(
        self,
        to_email: str,
        template_id: str,
        template_data: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a templated email message."""
        pass

    @abstractmethod
    async def verify_configuration(self) -> bool:
        """Verify provider credentials and reachability."""
        pass
