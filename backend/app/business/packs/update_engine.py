"""Business Pack Update & Conflict Management Engine (Spec E1, Phase 5)."""
import os
import hashlib
import json
import difflib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.snowflake import generate_snowflake_id
from app.business.packs.loader import BusinessPackLoader
from app.business.packs.models import BusinessAssetOverrideModel, BusinessPackModel
from app.business.packs.schemas import UpdateConflictRecord, PackManifest


class PackUpdateEngine:
    """Động cơ kiểm tra, nạp và xử lý xung đột cập nhật gói tri thức kinh doanh."""

    def __init__(self, loader: Optional[BusinessPackLoader] = None, updates_dir: Optional[Path] = None):
        self.loader = loader or BusinessPackLoader()
        base_dir = Path(__file__).resolve().parent
        self.updates_dir = updates_dir or (base_dir / "updates")
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    def compute_sha256(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def check_for_updates(
        self,
        db: AsyncSession,
        workspace_id: int,
        pack_id: str,
        update_manifest: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Kiểm tra bản cập nhật mới và phát hiện các điểm xung đột với Company Overrides."""
        current_manifest = self.loader.load_pack_manifest(pack_id)
        if not current_manifest:
            return {"update_available": False, "reason": f"Pack '{pack_id}' not found"}

        # Nếu không truyền manifest, tìm trong updates/available/{pack_id}.json
        if not update_manifest:
            update_file = self.updates_dir / "available" / f"{pack_id}.json"
            if update_file.exists():
                try:
                    with open(update_file, "r", encoding="utf-8") as f:
                        update_manifest = json.load(f)
                except Exception:
                    update_manifest = None

        if not update_manifest:
            return {
                "update_available": False,
                "current_version": current_manifest.version,
                "latest_version": current_manifest.version,
                "conflicts": [],
            }

        new_version = update_manifest.get("version", current_manifest.version)
        if new_version == current_manifest.version:
            return {
                "update_available": False,
                "current_version": current_manifest.version,
                "latest_version": new_version,
                "conflicts": [],
            }

        # 1. Lấy danh sách Company Overrides hiện hữu
        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.pack_id == pack_id,
                BusinessAssetOverrideModel.is_active.is_(True),
            )
        )
        res = await db.execute(stmt)
        overrides = {o.asset_id: o for o in res.scalars().all()}

        # 2. Phát hiện xung đột: Tài sản nào có trong update mà Company đã override?
        conflicts = []
        for updated_file in update_manifest.get("files", []):
            path_str = updated_file.get("path", "")
            # Mapping path sang asset_id, vd: templates/nda-vn/template.yaml -> governance.templates.nda-vn
            parts = path_str.split("/")
            if len(parts) >= 2:
                asset_category = parts[0]  # templates, sops, capabilities
                asset_name = parts[1]
                asset_id = f"{pack_id}.{asset_category}.{asset_name}"
                if asset_id in overrides:
                    conflicts.append({
                        "asset_id": asset_id,
                        "asset_type": asset_category[:-1] if asset_category.endswith("s") else asset_category,
                        "old_factory_version": current_manifest.version,
                        "new_factory_version": new_version,
                        "company_override_version": overrides[asset_id].version,
                        "status": "pending",
                        "requires_admin_review": True,
                        "path": path_str,
                    })

        return {
            "update_available": True,
            "current_version": current_manifest.version,
            "latest_version": new_version,
            "release_notes": update_manifest.get("release_notes", ""),
            "breaking": update_manifest.get("breaking", False),
            "files_count": len(update_manifest.get("files", [])),
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
        }

    def generate_diff(self, old_text: str, new_text: str, from_label: str = "Old", to_label: str = "New") -> str:
        """Tạo bản diff chi tiết dạng unified diff."""
        diff = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=from_label,
            tofile=to_label,
        )
        return "".join(diff)

    async def apply_resolution(
        self,
        db: AsyncSession,
        workspace_id: int,
        asset_id: str,
        resolution: str,  # KEEP_COMPANY, ACCEPT_FACTORY, MERGE, RESET_FACTORY
        merged_body: Optional[str] = None,
        merged_metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Thực thi lựa chọn giải quyết xung đột cập nhật của Admin."""
        resolution = resolution.upper()
        stmt = select(BusinessAssetOverrideModel).where(
            and_(
                BusinessAssetOverrideModel.workspace_id == workspace_id,
                BusinessAssetOverrideModel.asset_id == asset_id,
            )
        )
        res = await db.execute(stmt)
        record = res.scalars().first()

        if not record and resolution != "ACCEPT_FACTORY":
            return {"status": "error", "message": f"Asset override for '{asset_id}' not found"}

        if resolution == "KEEP_COMPANY":
            # Giữ nguyên bản của doanh nghiệp, không thay đổi gì
            return {
                "status": "success",
                "resolution": "KEEP_COMPANY",
                "message": "Company override preserved intact.",
                "active_version": record.version if record else "1.0.0",
            }

        elif resolution in ["ACCEPT_FACTORY", "RESET_FACTORY"]:
            # Chấp nhận Factory mới hoặc Reset hoàn toàn về Factory
            if record:
                await db.delete(record)
                await db.flush()
            return {
                "status": "success",
                "resolution": resolution,
                "message": "Reverted/Updated directly to Factory default.",
            }

        elif resolution == "MERGE":
            # Gộp nội dung tùy chỉnh và cập nhật override
            if record:
                if merged_metadata:
                    record.content_override_jsonb = merged_metadata
                if merged_body is not None:
                    record.body_override_markdown = merged_body
                record.updated_by = user_id
                record.updated_at = datetime.now(timezone.utc)
                await db.flush()
                return {
                    "status": "success",
                    "resolution": "MERGE",
                    "message": "Changes merged successfully into Company Override.",
                }

        return {"status": "error", "message": f"Invalid resolution strategy: {resolution}"}
