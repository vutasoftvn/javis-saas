import difflib
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import (
    ToolDefinition, PlatformToolVersion,
    PlatformPromptTemplate, PlatformPromptVersion
)
from app.workforce.registry.defaults import DEFAULT_TOOL_MANIFESTS, DEFAULT_PROMPT_TEMPLATES
from app.core.snowflake import generate_snowflake_id


class SkillVersioningService:
    """Quản lý phiên bản (Versioning), tính toán Diff và Khôi phục mặc định (Reset to Default)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Tool Versioning & Reset ---

    async def update_tool_spec(
        self,
        key: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        config: Dict[str, Any],
        workspace_id: Optional[int] = None,
        updated_by: Optional[int] = None,
        change_note: Optional[str] = None,
    ) -> ToolDefinition:
        stmt = select(ToolDefinition).where(ToolDefinition.key == key)
        if workspace_id is not None:
            stmt = stmt.where(ToolDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        tool = res.scalars().first()
        if not tool:
            raise ValueError(f"Tool '{key}' not found")

        # Lưu version cũ trước khi update
        version_entry = PlatformToolVersion(
            id=generate_snowflake_id(),
            tool_id=tool.id,
            version=tool.version,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            config_jsonb=tool.config_jsonb,
            change_note=change_note or f"Updated to version {tool.version + 1}",
            created_by=updated_by,
            created_at=datetime.utcnow(),
        )
        self.db.add(version_entry)

        # Cập nhật tool lên version mới
        tool.version += 1
        tool.input_schema = input_schema
        tool.output_schema = output_schema
        tool.config_jsonb = config
        await self.db.flush()
        return tool

    async def reset_tool_to_default(
        self,
        key: str,
        workspace_id: Optional[int] = None,
        updated_by: Optional[int] = None,
    ) -> ToolDefinition:
        # Tìm manifest gốc
        default_manifest = next((m for m in DEFAULT_TOOL_MANIFESTS if m["key"] == key), None)
        if not default_manifest:
            raise ValueError(f"No factory default manifest found for tool '{key}'")

        return await self.update_tool_spec(
            key=key,
            input_schema=default_manifest.get("input_schema", {}),
            output_schema=default_manifest.get("output_schema", {}),
            config=default_manifest.get("config", {}),
            workspace_id=workspace_id,
            updated_by=updated_by,
            change_note="Reset to Factory Default",
        )

    async def get_tool_versions(self, tool_id: int) -> List[PlatformToolVersion]:
        stmt = select(PlatformToolVersion).where(PlatformToolVersion.tool_id == tool_id).order_by(desc(PlatformToolVersion.version))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # --- Prompt Versioning, Diff & Reset ---

    async def get_prompt_diff(
        self,
        key: str,
        workspace_id: Optional[int] = None,
        target_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Tạo bản so sánh (diff) trực quan giữa Prompt hiện tại và Default / Version cũ."""
        stmt = select(PlatformPromptTemplate).where(PlatformPromptTemplate.key == key)
        if workspace_id is not None:
            stmt = stmt.where(PlatformPromptTemplate.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        tmpl = res.scalars().first()
        if not tmpl:
            raise ValueError(f"Prompt template '{key}' not found")

        current_content = tmpl.current_content
        compare_content = tmpl.default_content

        if target_version is not None:
            # Tra cứu version cụ thể trong lịch sử
            v_stmt = select(PlatformPromptVersion).where(
                and_(
                    PlatformPromptVersion.template_id == tmpl.id,
                    PlatformPromptVersion.version == target_version,
                )
            )
            v_res = await self.db.execute(v_stmt)
            old_ver = v_res.scalars().first()
            if old_ver:
                compare_content = old_ver.content

        diff_lines = list(
            difflib.unified_diff(
                compare_content.splitlines(keepends=True),
                current_content.splitlines(keepends=True),
                fromfile=f"version_{target_version or 'default'}",
                tofile=f"version_{tmpl.current_version}",
            )
        )

        return {
            "key": key,
            "current_version": tmpl.current_version,
            "compared_to": target_version or "default",
            "diff_text": "".join(diff_lines),
            "is_modified_from_default": current_content.strip() != tmpl.default_content.strip(),
        }

    async def reset_prompt_to_default(
        self,
        key: str,
        workspace_id: Optional[int] = None,
        restored_by: Optional[int] = None,
    ) -> PlatformPromptTemplate:
        stmt = select(PlatformPromptTemplate).where(PlatformPromptTemplate.key == key)
        if workspace_id is not None:
            stmt = stmt.where(PlatformPromptTemplate.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        tmpl = res.scalars().first()

        default_text = DEFAULT_PROMPT_TEMPLATES.get(key, "")
        if not tmpl:
            tmpl = PlatformPromptTemplate(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                key=key,
                default_content=default_text,
                current_content=default_text,
                current_version=1,
                updated_by=restored_by,
            )
            self.db.add(tmpl)
        else:
            # Lưu version hiện tại trước khi reset
            v_entry = PlatformPromptVersion(
                id=generate_snowflake_id(),
                template_id=tmpl.id,
                version=tmpl.current_version,
                content=tmpl.current_content,
                change_note="Reset to Factory Default",
                created_by=restored_by,
            )
            self.db.add(v_entry)
            tmpl.current_content = tmpl.default_content or default_text
            tmpl.current_version += 1
            tmpl.updated_by = restored_by

        await self.db.flush()
        return tmpl
