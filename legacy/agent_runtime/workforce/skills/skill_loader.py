import os
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

try:
    import yaml
except ImportError:
    yaml = None

from workforce.models import AgentDefinition, ToolDefinition, AgentToolPermission
from workforce.registry.tool_registry import ToolRegistryService
from workforce.skills.skill_registry import SkillRegistryService
from workforce.governance.permission_engine import UnifiedPermissionEngine


class PhysicalSkillDocument:
    """Đại diện cho một file SKILL.md có cấu trúc YAML Frontmatter + Markdown Body."""

    def __init__(
        self,
        skill_id: str,
        name: str,
        department: str,
        version: str,
        description: str,
        risk_level: str,
        required_tools: List[str],
        content_markdown: str,
        file_path: str,
        content_hash: str,
    ):
        self.skill_id = skill_id
        self.name = name
        self.department = department
        self.version = version
        self.description = description
        self.risk_level = risk_level
        self.required_tools = required_tools
        self.content_markdown = content_markdown
        self.file_path = file_path
        self.content_hash = content_hash

    @classmethod
    def from_file(cls, path: Path) -> Optional["PhysicalSkillDocument"]:
        if not path.exists() or not path.name.endswith(".md"):
            return None

        text = path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Parse YAML frontmatter
        frontmatter = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                raw_yaml = parts[1]
                body = parts[2].strip()
                if yaml:
                    try:
                        frontmatter = yaml.safe_load(raw_yaml) or {}
                    except Exception:
                        pass
                else:
                    # Fallback simple line parser
                    for line in raw_yaml.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter[k.strip()] = v.strip()

        # Domain normalization mapping
        domain_mapping = {
            "sales": "sales",
            "marketing": "marketing",
            "growth": "marketing",
            "finance": "finance",
            "legal": "legal",
            "governance": "legal",
            "operations": "operations",
            "people": "operations",
            "talent": "operations",
            "training": "operations",
            "reporting": "operations",
            "customer": "operations",
            "tech": "tech",
            "engineering": "tech",
            "product-tech": "tech",
            "product": "tech",
        }

        # Extract domain from frontmatter or path parts
        raw_dept = frontmatter.get("department") or frontmatter.get("domain")
        if not raw_dept:
            path_str = str(path).lower()
            for k in domain_mapping:
                if f"/{k}/" in path_str:
                    raw_dept = k
                    break
        raw_dept = (raw_dept or "general").lower()
        department = domain_mapping.get(raw_dept, raw_dept)

        skill_id = frontmatter.get("id", path.parent.name)
        name = frontmatter.get("name", skill_id.replace("_", " ").replace("-", " ").title())
        version = str(frontmatter.get("version", "1.0.0"))
        description = frontmatter.get("description", "")
        risk_level = frontmatter.get("risk_level", "low")
        required_tools = frontmatter.get("required_tools", [])

        return cls(
            skill_id=skill_id,
            name=name,
            department=department,
            version=version,
            description=description,
            risk_level=risk_level,
            required_tools=required_tools if isinstance(required_tools, list) else [],
            content_markdown=body,
            file_path=str(path),
            content_hash=content_hash,
        )


class DynamicSkillLoader:
    """Nạp danh sách Tools/Skills động cho Agent dựa trên ma trận phân quyền thực tế và kho SKILL.md."""

    def __init__(self, db: Optional[AsyncSession] = None, skills_root_dir: Optional[str] = None):
        self.db = db
        self.skills_root = Path(skills_root_dir) if skills_root_dir else Path(__file__).parent
        self.app_root = self.skills_root.parent.parent
        self.registry = ToolRegistryService(db) if db is not None else None
        self.permission_engine = UnifiedPermissionEngine(db) if db is not None else None

    def scan_physical_skills(self) -> List[PhysicalSkillDocument]:
        """Quét toàn bộ thư mục skills và business packs để lấy danh sách SKILL.md vật lý."""
        skills: List[PhysicalSkillDocument] = []
        scanned_paths = set()

        search_dirs = [
            self.skills_root,
            self.app_root / "business" / "packs" / "factory",
            self.app_root / "workforce" / "agents" / "skills_library",
        ]

        for s_dir in search_dirs:
            if not s_dir.exists():
                continue
            for p in s_dir.rglob("*.md"):
                if p.name.upper() == "SKILL.MD" or "SKILL" in p.name.upper():
                    real_path = str(p.resolve())
                    if real_path not in scanned_paths:
                        scanned_paths.add(real_path)
                        doc = PhysicalSkillDocument.from_file(p)
                        if doc:
                            skills.append(doc)
        return skills

    def load_relevant_skills_for_task(
        self,
        task_description: str,
        department: Optional[str] = None,
        max_skills: int = 3,
    ) -> List[PhysicalSkillDocument]:
        """Nạp On-Demand các Skill có liên quan trực tiếp đến Task (không inject all)."""
        all_skills = self.scan_physical_skills()
        if not all_skills:
            return []

        scored_skills = []
        desc_lower = task_description.lower()

        for s in all_skills:
            score = 0
            if department and s.department.lower() == department.lower():
                score += 5
            # Matching keywords
            for kw in [s.skill_id, s.name, s.department]:
                if kw.lower() in desc_lower:
                    score += 10
            for tool_kw in s.required_tools:
                if tool_kw.lower() in desc_lower:
                    score += 4
            
            # Default inclusion for matching department
            if score > 0:
                scored_skills.append((score, s))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored_skills[:max_skills]]

    async def load_tools_for_agent(
        self,
        agent: AgentDefinition,
        workspace_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Nạp danh sách schema tools chuẩn hóa mà Agent được phép gọi."""
        if not self.registry or not self.permission_engine:
            return []

        all_tools = await self.registry.list_tools(workspace_id=workspace_id, enabled_only=True)
        if not all_tools:
            all_tools = await self.registry.list_tools(workspace_id=None, enabled_only=True)

        allowed_tool_schemas: List[Dict[str, Any]] = []

        for tool in all_tools:
            can_execute = await self.permission_engine.can(
                principal_type="AGENT",
                principal_id=agent.id,
                resource_type="TOOL",
                resource_key=tool.key,
                action="EXECUTE",
                workspace_id=workspace_id,
            )

            if can_execute:
                formatted_schema = {
                    "type": "function",
                    "function": {
                        "name": tool.key,
                        "description": tool.description or tool.name,
                        "parameters": tool.input_schema if tool.input_schema else {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Tham số truy vấn chính"},
                                "params": {"type": "object", "description": "Dữ liệu cấu hình bổ sung"},
                            },
                        }
                    }
                }
                allowed_tool_schemas.append(formatted_schema)

        return allowed_tool_schemas

