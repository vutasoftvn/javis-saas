from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import PlatformPromptTemplate, PlatformPromptVersion
from workforce.registry.defaults import DEFAULT_PROMPT_TEMPLATES
from core.snowflake import generate_snowflake_id


class PromptRegistryService:
    """Service quản lý Prompt Templates, versioning và cơ chế Restore Default."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_prompt_template(self, key: str, workspace_id: Optional[int] = None) -> Optional[PlatformPromptTemplate]:
        stmt = select(PlatformPromptTemplate).where(PlatformPromptTemplate.key == key)
        if workspace_id is not None:
            stmt = stmt.where(PlatformPromptTemplate.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_prompt_content(self, key: str, workspace_id: Optional[int] = None) -> str:
        """Lấy nội dung prompt đang active, nếu chưa có trong DB thì fallback về default manifest."""
        tmpl = await self.get_prompt_template(key, workspace_id)
        if tmpl:
            return tmpl.current_content
        return DEFAULT_PROMPT_TEMPLATES.get(key, f"System prompt for {key}")

    async def update_prompt_content(
        self,
        key: str,
        new_content: str,
        workspace_id: Optional[int] = None,
        updated_by: Optional[int] = None,
        change_note: Optional[str] = None
    ) -> PlatformPromptTemplate:
        """Cập nhật nội dung prompt và lưu lại version cũ vào prompt_versions."""
        tmpl = await self.get_prompt_template(key, workspace_id)
        default_val = DEFAULT_PROMPT_TEMPLATES.get(key, new_content)

        if not tmpl:
            tmpl = PlatformPromptTemplate(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                key=key,
                default_content=default_val,
                current_content=new_content,
                current_version=1,
                updated_by=updated_by,
            )
            self.db.add(tmpl)
            await self.db.flush()
            version_entry = PlatformPromptVersion(
                id=generate_snowflake_id(),
                template_id=tmpl.id,
                version=1,
                content=new_content,
                change_note=change_note or "Initial version",
                created_by=updated_by,
            )
            self.db.add(version_entry)
            await self.db.flush()
            return tmpl

        # Lưu version mới
        new_ver_num = tmpl.current_version + 1
        tmpl.current_content = new_content
        tmpl.current_version = new_ver_num
        tmpl.updated_by = updated_by

        version_entry = PlatformPromptVersion(
            id=generate_snowflake_id(),
            template_id=tmpl.id,
            version=new_ver_num,
            content=new_content,
            change_note=change_note or f"Updated to version {new_ver_num}",
            created_by=updated_by,
        )
        self.db.add(version_entry)
        await self.db.flush()
        return tmpl

    async def restore_default(
        self,
        key: str,
        workspace_id: Optional[int] = None,
        restored_by: Optional[int] = None
    ) -> Optional[PlatformPromptTemplate]:
        """Khôi phục prompt về bản mặc định gốc từ Factory Manifests."""
        default_val = DEFAULT_PROMPT_TEMPLATES.get(key)
        if not default_val:
            return None
        return await self.update_prompt_content(
            key=key,
            new_content=default_val,
            workspace_id=workspace_id,
            updated_by=restored_by,
            change_note="Restored to Factory Default"
        )
