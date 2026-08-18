"""Business Pack Loader: Discovers and parses Factory and Company packs from filesystem."""
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml

from app.business.packs.schemas import (
    PackManifest,
    CapabilityDefinition,
    SOPDefinition,
    TemplateMetadata,
    TemplateBundle,
    LegalSourceMetadata,
    SkillDefinition,
)


class BusinessPackLoader:
    """Nạp các gói tri thức kinh doanh (Business Knowledge Packs) từ thư mục local."""

    def __init__(self, factory_root: Optional[Path] = None, company_root: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent
        self.factory_root = factory_root or (base_dir / "factory")
        self.company_root = company_root or (base_dir / "company")

    def list_factory_pack_ids(self) -> List[str]:
        if not self.factory_root.exists():
            return []
        packs = []
        for p in self.factory_root.iterdir():
            if p.is_dir() and (p / "pack.yaml").exists():
                packs.append(p.name)
        return sorted(packs)

    def load_pack_manifest(self, pack_id: str) -> Optional[PackManifest]:
        pack_dir = self.factory_root / pack_id
        manifest_file = pack_dir / "pack.yaml"
        if not manifest_file.exists():
            return None
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "id" not in data:
                    data["id"] = pack_id
                return PackManifest(**data)
        except Exception:
            return None

    def list_capabilities(self, pack_id: str) -> List[CapabilityDefinition]:
        cap_dir = self.factory_root / pack_id / "capabilities"
        if not cap_dir.exists():
            return []
        items = []
        for f in sorted(cap_dir.glob("*.yaml")):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}
                    if "domain" not in data:
                        data["domain"] = pack_id
                    items.append(CapabilityDefinition(**data))
            except Exception:
                continue
        return items

    def get_capability(self, pack_id: str, cap_id: str) -> Optional[CapabilityDefinition]:
        # cap_id can be 'create_nda' or 'governance.create_nda' or 'create-nda'
        clean_name = cap_id.split(".")[-1].replace("_", "-")
        cap_file = self.factory_root / pack_id / "capabilities" / f"{clean_name}.yaml"
        if not cap_file.exists():
            # Try underscore version
            clean_name_underscore = cap_id.split(".")[-1].replace("-", "_")
            cap_file = self.factory_root / pack_id / "capabilities" / f"{clean_name_underscore}.yaml"
        if not cap_file.exists():
            return None
        try:
            with open(cap_file, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
                if "domain" not in data:
                    data["domain"] = pack_id
                return CapabilityDefinition(**data)
        except Exception:
            return None

    def list_sops(self, pack_id: str) -> List[SOPDefinition]:
        sop_dir = self.factory_root / pack_id / "sops"
        if not sop_dir.exists():
            return []
        items = []
        for f in sorted(sop_dir.glob("*.yaml")):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}
                    items.append(SOPDefinition(**data))
            except Exception:
                continue
        return items

    def get_sop(self, pack_id: str, sop_id: str) -> Optional[SOPDefinition]:
        clean_name = sop_id.split(".")[-1].replace("_", "-")
        sop_file = self.factory_root / pack_id / "sops" / f"{clean_name}.yaml"
        if not sop_file.exists():
            clean_name_underscore = sop_id.split(".")[-1].replace("-", "_")
            sop_file = self.factory_root / pack_id / "sops" / f"{clean_name_underscore}.yaml"
        if not sop_file.exists():
            return None
        try:
            with open(sop_file, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
                return SOPDefinition(**data)
        except Exception:
            return None

    def list_templates(self, pack_id: str) -> List[TemplateMetadata]:
        tpl_dir = self.factory_root / pack_id / "templates"
        if not tpl_dir.exists():
            return []
        items = []
        for p in sorted(tpl_dir.iterdir()):
            if p.is_dir() and (p / "template.yaml").exists():
                try:
                    with open(p / "template.yaml", "r", encoding="utf-8") as file:
                        data = yaml.safe_load(file) or {}
                        if "id" not in data:
                            data["id"] = p.name
                        items.append(TemplateMetadata(**data))
                except Exception:
                    continue
        return items

    def get_template_bundle(self, pack_id: str, template_id: str) -> Optional[TemplateBundle]:
        clean_name = template_id.split(".")[-1]
        tpl_dir = self.factory_root / pack_id / "templates" / clean_name
        meta_file = tpl_dir / "template.yaml"
        body_file = tpl_dir / "body.md"
        if not meta_file.exists() or not body_file.exists():
            return None
        try:
            with open(meta_file, "r", encoding="utf-8") as mf:
                meta_data = yaml.safe_load(mf) or {}
                if "id" not in meta_data:
                    meta_data["id"] = clean_name
                metadata = TemplateMetadata(**meta_data)
            with open(body_file, "r", encoding="utf-8") as bf:
                body = bf.read()
            return TemplateBundle(metadata=metadata, body_markdown=body, is_override=False)
        except Exception:
            return None

    def list_legal_sources(self, pack_id: str) -> List[LegalSourceMetadata]:
        sources_dir = self.factory_root / pack_id / "legal" / "sources"
        if not sources_dir.exists():
            return []
        items = []
        for p in sorted(sources_dir.iterdir()):
            if p.is_dir() and (p / "metadata.yaml").exists():
                try:
                    with open(p / "metadata.yaml", "r", encoding="utf-8") as file:
                        data = yaml.safe_load(file) or {}
                        if "id" not in data:
                            data["id"] = p.name
                        items.append(LegalSourceMetadata(**data))
                except Exception:
                    continue
        return items

    def get_legal_source_content(self, pack_id: str, source_id: str) -> Optional[str]:
        source_dir = self.factory_root / pack_id / "legal" / "sources" / source_id
        text_file = source_dir / "normalized.md"
        if text_file.exists():
            return text_file.read_text(encoding="utf-8")
        return None

    def list_skills(self, pack_id: str) -> List[SkillDefinition]:
        skills_dir = self.factory_root / pack_id / "skills"
        if not skills_dir.exists():
            return []
        items = []
        for p in sorted(skills_dir.iterdir()):
            if p.is_dir() and (p / "SKILL.md").exists():
                skill_obj = self.get_skill(pack_id, p.name)
                if skill_obj:
                    items.append(skill_obj)
        return items

    def get_skill(self, pack_id: str, skill_id: str) -> Optional[SkillDefinition]:
        clean_name = skill_id.split(".")[-1].replace("_", "-")
        skill_file = self.factory_root / pack_id / "skills" / clean_name / "SKILL.md"
        if not skill_file.exists():
            return None
        try:
            content = skill_file.read_text(encoding="utf-8")
            meta = {}
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
            if "id" not in meta:
                meta["id"] = clean_name
            if "name" not in meta:
                meta["name"] = clean_name.replace("-", " ").title()
            if "domain" not in meta:
                meta["domain"] = pack_id
            meta["body_markdown"] = body
            return SkillDefinition(**meta)
        except Exception:
            return None

