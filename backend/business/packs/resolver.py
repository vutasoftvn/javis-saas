"""Business Pack Asset Resolver: Resolves assets with Company Override priority over Factory Default."""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from business.packs.loader import BusinessPackLoader
from business.packs.models import BusinessAssetOverrideModel
from business.packs.schemas import (
    TemplateBundle,
    CapabilityDefinition,
    SOPDefinition,
)


class BusinessPackResolver:
    """Động cơ phân giải tài sản tri thức kinh doanh (Asset Resolution Engine).
    
    Quy tắc phân giải bất biến:
        Company Override (Ưu tiên cao nhất) -> Factory Default (Dự phòng chuẩn)
    """

    def __init__(self, loader: Optional[BusinessPackLoader] = None):
        self.loader = loader or BusinessPackLoader()

    async def resolve_template(
        self,
        db: AsyncSession,
        workspace_id: int,
        pack_id: str,
        template_id: str,
    ) -> Optional[TemplateBundle]:
        """Phân giải Template: kiểm tra Company Override trước, fallback về Factory."""
        clean_tpl_id = template_id.split(".")[-1]
        asset_key = f"{pack_id}.templates.{clean_tpl_id}"

        # 1. Tra cứu Company Override trong DB
        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.asset_id == asset_key,
                BusinessAssetOverrideModel.is_active.is_(True),
            )
        )
        res = await db.execute(stmt)
        override = res.scalars().first()

        # 2. Lấy Factory Default làm base
        factory_bundle = self.loader.get_template_bundle(pack_id, clean_tpl_id)
        if not factory_bundle:
            return None

        if override:
            # Tạo bundle override kết hợp
            meta_update = override.content_override_jsonb.get("metadata", {})
            metadata = (
                factory_bundle.metadata.model_copy(update=meta_update)
                if hasattr(factory_bundle.metadata, "model_copy")
                else factory_bundle.metadata.copy(update=meta_update)
            )
            body = override.body_override_markdown or factory_bundle.body_markdown
            return TemplateBundle(
                metadata=metadata,
                body_markdown=body,
                is_override=True,
                override_version=override.version,
            )

        return factory_bundle

    async def resolve_sop(
        self,
        db: AsyncSession,
        workspace_id: int,
        pack_id: str,
        sop_id: str,
    ) -> Optional[SOPDefinition]:
        """Phân giải SOP: kiểm tra Company Override trước, fallback về Factory."""
        clean_sop_id = sop_id.split(".")[-1].replace("_", "-")
        asset_key = f"{pack_id}.sops.{clean_sop_id}"

        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.asset_id == asset_key,
                BusinessAssetOverrideModel.is_active.is_(True),
            )
        )
        res = await db.execute(stmt)
        override = res.scalars().first()

        factory_sop = self.loader.get_sop(pack_id, clean_sop_id)
        if not factory_sop:
            return None

        if override and override.content_override_jsonb:
            override_data = (
                factory_sop.model_dump()
                if hasattr(factory_sop, "model_dump")
                else factory_sop.dict()
            )
            override_data.update(override.content_override_jsonb)
            return SOPDefinition(**override_data)

        return factory_sop

    async def resolve_capability(
        self,
        db: AsyncSession,
        workspace_id: int,
        pack_id: str,
        capability_id: str,
    ) -> Optional[CapabilityDefinition]:
        """Phân giải Capability Definition."""
        clean_cap_id = capability_id.split(".")[-1].replace("_", "-")
        asset_key = f"{pack_id}.capabilities.{clean_cap_id}"

        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.asset_id == asset_key,
                BusinessAssetOverrideModel.is_active.is_(True),
            )
        )
        res = await db.execute(stmt)
        override = res.scalars().first()

        factory_cap = self.loader.get_capability(pack_id, clean_cap_id)
        if not factory_cap:
            return None

        if override and override.content_override_jsonb:
            override_data = (
                factory_cap.model_dump()
                if hasattr(factory_cap, "model_dump")
                else factory_cap.dict()
            )
            override_data.update(override.content_override_jsonb)
            return CapabilityDefinition(**override_data)

        return factory_cap
