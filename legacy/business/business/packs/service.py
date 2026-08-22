"""High-level Business Pack Service for COSA."""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.snowflake import generate_snowflake_id
from business.packs.loader import BusinessPackLoader
from business.packs.resolver import BusinessPackResolver
from business.packs.legal_resolver import LegalKnowledgeResolver
from business.packs.models import BusinessAssetOverrideModel, BusinessPackModel
from business.packs.schemas import PackManifest, TemplateBundle, CapabilityDefinition, SOPDefinition


class BusinessPackService:
    """Service điều phối toàn bộ vòng đời Business Knowledge Pack."""

    def __init__(
        self,
        loader: Optional[BusinessPackLoader] = None,
        resolver: Optional[BusinessPackResolver] = None,
        legal_resolver: Optional[LegalKnowledgeResolver] = None,
    ):
        self.loader = loader or BusinessPackLoader()
        self.resolver = resolver or BusinessPackResolver(self.loader)
        self.legal_resolver = legal_resolver or LegalKnowledgeResolver(self.loader)

    async def list_available_packs(self, db: AsyncSession, workspace_id: int) -> List[Dict[str, Any]]:
        pack_ids = self.loader.list_factory_pack_ids()
        results = []
        for pid in pack_ids:
            manifest = self.loader.load_pack_manifest(pid)
            if not manifest:
                continue
            
            caps = self.loader.list_capabilities(pid)
            templates = self.loader.list_templates(pid)
            sops = self.loader.list_sops(pid)
            
            # Count overrides for this workspace
            stmt = select(BusinessAssetOverrideModel).where(
                and_(
                    BusinessAssetOverrideModel.workspace_id == workspace_id,
                    BusinessAssetOverrideModel.pack_id == pid,
                    BusinessAssetOverrideModel.is_active.is_(True),
                )
            )
            res = await db.execute(stmt)
            overrides = list(res.scalars().all())

            results.append({
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "status": manifest.status,
                "capabilities_count": len(caps),
                "templates_count": len(templates),
                "sops_count": len(sops),
                "overrides_count": len(overrides),
                "update_available": False,
            })
        return results

    async def get_pack_details(self, db: AsyncSession, workspace_id: int, pack_id: str) -> Optional[Dict[str, Any]]:
        manifest = self.loader.load_pack_manifest(pack_id)
        if not manifest:
            return None

        caps = self.loader.list_capabilities(pack_id)
        templates = self.loader.list_templates(pack_id)
        sops = self.loader.list_sops(pack_id)
        legal_sources = self.loader.list_legal_sources(pack_id)

        # Get overrides map
        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.pack_id == pack_id,
                BusinessAssetOverrideModel.is_active.is_(True),
            )
        )
        res = await db.execute(stmt)
        overrides = {o.asset_id: o for o in res.scalars().all()}

        def _dump(obj: Any) -> Dict[str, Any]:
            return obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()

        return {
            "manifest": _dump(manifest),
            "capabilities": [_dump(c) for c in caps],
            "templates": [
                {
                    **_dump(t),
                    "is_overridden": f"{pack_id}.templates.{t.id}" in overrides,
                }
                for t in templates
            ],
            "sops": [
                {
                    **_dump(s),
                    "is_overridden": f"{pack_id}.sops.{s.id.split('.')[-1]}" in overrides,
                }
                for s in sops
            ],
            "legal_sources": [_dump(ls) for ls in legal_sources],
            "overrides_count": len(overrides),
        }

    async def create_or_update_override(
        self,
        db: AsyncSession,
        workspace_id: int,
        pack_id: str,
        asset_id: str,
        asset_type: str,
        content_override: Dict[str, Any],
        body_override: Optional[str] = None,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> BusinessAssetOverrideModel:
        """Tạo hoặc cập nhật Company Override cho một tài sản."""
        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.asset_id == asset_id,
            )
        )
        res = await db.execute(stmt)
        record = res.scalars().first()

        if record:
            record.content_override_jsonb = content_override
            if body_override is not None:
                record.body_override_markdown = body_override
            record.is_active = True
            record.updated_by = user_id
            record.notes = notes
            await db.flush()
            return record

        record = BusinessAssetOverrideModel(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            asset_id=asset_id,
            asset_type=asset_type,
            pack_id=pack_id,
            version="1.0.0",
            content_override_jsonb=content_override,
            body_override_markdown=body_override,
            is_active=True,
            updated_by=user_id,
            notes=notes,
        )
        db.add(record)
        await db.flush()
        return record

    async def reset_to_factory(
        self,
        db: AsyncSession,
        workspace_id: int,
        asset_id: str,
    ) -> bool:
        """Khôi phục tài sản về Factory Default (xóa / vô hiệu hóa Company Override)."""
        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.asset_id == asset_id,
            )
        )
        res = await db.execute(stmt)
        record = res.scalars().first()
        if record:
            await db.delete(record)
            await db.flush()
            return True
        return False
