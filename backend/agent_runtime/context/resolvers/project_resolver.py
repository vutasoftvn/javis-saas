"""
COSA Project Scope Resolver
Nạp thông tin dự án mục tiêu khi thỏa mãn Explicit Context Rule (Structure.md Mục 16).
"""
from typing import Any, Dict, Optional


class ProjectScopeResolver:
    """Nạp ngữ cảnh dự án khi được yêu cầu tường minh"""

    @staticmethod
    async def resolve(project_id: str, db_session: Any = None) -> Dict[str, Any]:
        return {
            "project_id": project_id,
            "project_name": f"Project {project_id}",
            "stage": "MVP_VALIDATION",
            "active_okrs": ["Đạt 100 paid users", "Hoàn thiện MVP core"],
            "tasks_summary": {"total": 24, "completed": 16, "in_progress": 8}
        }
