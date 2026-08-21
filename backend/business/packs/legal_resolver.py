"""Legal Knowledge Resolver: Dynamic Legal Context Resolution with Immutable Sources & Company Annotations."""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from business.packs.loader import BusinessPackLoader
from business.packs.models import LegalSourceRecord, LegalAnnotationRecord
from business.packs.schemas import LegalSourceMetadata, CompanyLegalAnnotation


class LegalKnowledgeResolver:
    """Bộ phân giải ngữ cảnh pháp lý cho AI Agent và Capability Execution."""

    def __init__(self, loader: Optional[BusinessPackLoader] = None):
        self.loader = loader or BusinessPackLoader()

    async def resolve_legal_sources_for_capability(
        self,
        db: AsyncSession,
        workspace_id: int,
        pack_id: str,
        jurisdiction: str = "VN",
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Phân giải danh sách căn cứ pháp lý hiện hành kèm ghi chú của doanh nghiệp."""
        # 1. Quét các nguồn Factory Legal
        factory_sources = self.loader.list_legal_sources(pack_id)
        active_sources: List[Dict[str, Any]] = []

        for src in factory_sources:
            if src.jurisdiction != jurisdiction:
                continue

            # Quy tắc an toàn: Không dùng văn bản đã hết hiệu lực (expired)
            if src.status == "expired":
                continue

            # Lọc theo tags nếu được chỉ định
            if tags and not any(t in src.tags for t in tags):
                continue

            # 2. Lấy nội dung text nếu có
            text_content = self.loader.get_legal_source_content(pack_id, src.id)

            # 3. Tra cứu Company Annotation
            stmt = select(LegalAnnotationRecord).where(
                and_(
                    LegalAnnotationRecord.workspace_id == workspace_id,
                    LegalAnnotationRecord.legal_source_id == src.id,
                )
            )
            res = await db.execute(stmt)
            annotation = res.scalars().first()

            company_notes = annotation.notes if annotation else []
            applicability = annotation.applicability_status if annotation else "applicable"

            active_sources.append({
                "source_id": src.id,
                "title": src.title,
                "identifier": src.identifier,
                "issuer": src.issuer,
                "status": src.status,
                "version": src.version,
                "effective_date": src.effective_date,
                "tags": src.tags,
                "is_unverified": (src.status == "unknown"),
                "company_applicability": applicability,
                "company_notes": company_notes,
                "text_summary": text_content[:500] if text_content else None,
            })

        return active_sources

    async def add_or_update_annotation(
        self,
        db: AsyncSession,
        workspace_id: int,
        legal_source_id: str,
        applicability_status: str,
        notes: List[str],
        user_id: Optional[int] = None,
        linked_sops: Optional[List[str]] = None,
        linked_templates: Optional[List[str]] = None,
    ) -> LegalAnnotationRecord:
        """Ghi chú nội bộ của doanh nghiệp cho văn bản pháp lý (không sửa file nguồn gốc)."""
        stmt = select(LegalAnnotationRecord).where(
            and_(
                LegalAnnotationRecord.workspace_id == workspace_id,
                LegalAnnotationRecord.legal_source_id == legal_source_id,
            )
        )
        res = await db.execute(stmt)
        record = res.scalars().first()

        if record:
            record.applicability_status = applicability_status
            record.notes = notes
            if linked_sops is not None:
                record.linked_sops = linked_sops
            if linked_templates is not None:
                record.linked_templates = linked_templates
            record.reviewed_by = user_id
            await db.flush()
            return record

        from core.snowflake import generate_snowflake_id
        record = LegalAnnotationRecord(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            legal_source_id=legal_source_id,
            applicability_status=applicability_status,
            notes=notes,
            linked_sops=linked_sops or [],
            linked_templates=linked_templates or [],
            reviewed_by=user_id,
        )
        db.add(record)
        await db.flush()
        return record
