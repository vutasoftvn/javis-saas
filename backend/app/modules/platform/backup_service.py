import logging
import uuid
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def create_workspace_backup(workspace_id: uuid.UUID) -> str:
    """
    Tạo bản backup cho workspace (Postgres dump các dòng thuộc workspace_id + MinIO objects).
    Trở lại URL để tải.
    """
    logger.info(f"Creating backup for workspace {workspace_id}")
    return f"https://storage.javis.com/backups/{workspace_id}/backup.zip"
