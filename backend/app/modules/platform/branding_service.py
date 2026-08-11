import logging
import uuid
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def get_workspace_branding(workspace_id: uuid.UUID) -> Dict[str, Any]:
    """
    Lấy thông tin branding của workspace (logo, primary color, v.v).
    Trong MVP trả về mặc định.
    """
    return {
        "primary_color": "#007BFF",
        "logo_url": None,
        "name": "My Workspace"
    }
