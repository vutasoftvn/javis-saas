"""Stage-Aware Workforce Service

Kết nối ManagementPolicyEngine với AgentDefinition trong DB để trả về
danh sách agent được xếp hạng và phân loại theo Stage context hiện tại.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from workforce.models import AgentDefinition
from founder_os.strategy.services.management_policy_engine import ManagementPolicyEngine
from founder_os.strategy.schemas.stage_schemas import ProjectStageEnum


@dataclass
class AgentWithStageFit:
    """Agent Definition bổ sung metadata về mức độ phù hợp với Stage hiện tại."""
    # Base AgentDefinition fields
    id: int
    key: str
    name: str
    role_title: Optional[str]
    department: Optional[str]
    description: Optional[str]
    agent_type: str
    default_model_profile: str
    risk_level: int
    status: str
    enabled: bool
    is_system: bool

    # Stage-fit metadata (Phase 6)
    priority: str           # 'HIGH' | 'MEDIUM' | 'LOW'
    fit_score: int          # 0–100
    is_locked: bool         # True nếu domain thuộc deemphasized_tools của stage
    stage_recommendation: str  # Lý do được ưu tiên / bị lock


# Mapping agent name patterns → domain keywords để so sánh với deemphasized_tools
# Key: agent key prefix / name keyword → domains liên quan
_AGENT_DOMAIN_MAP: Dict[str, List[str]] = {
    "founder_copilot": [],  # Executive — luôn available
    "general": [],          # General — luôn available
    "cfo_agent": ["bsc", "nps", "churn", "scale_metrics", "heavy_sop", "crm_pipeline"],
    "cmo_agent": ["paid_ads", "growth_funnel", "channel_scaling"],
    "sales_agent": ["crm_pipeline", "channel_scaling", "paid_ads"],
    "tech_lead_agent": ["full_sop", "complex_org_hierarchy", "department_okrs"],
    "developer": [],
    "devops_agent": [],
    "legal_agent": ["complex_org_hierarchy", "department_okrs", "compliance_audit"],
    "hr_agent": ["department_okrs", "complex_org_hierarchy", "heavy_sop"],
    "product_agent": ["bsc", "departmental_okrs", "nps_large_scale", "channel_scaling"],
    "data_analyst_agent": ["bsc", "department_okrs"],
}

# Mapping priority_agents name → agent key để tra cứu
_PRIORITY_NAME_TO_KEY: Dict[str, str] = {
    "Research Agent": "general",
    "Customer Agent": "cmo_agent",
    "Product Agent": "product_agent",
    "Tech Agent": "tech_lead_agent",
    "Finance Agent": "cfo_agent",
    "Sales Agent": "sales_agent",
    "Marketing Agent": "cmo_agent",
    "Execution Agent": "founder_copilot",
    "Legal Agent": "legal_agent",
}


class StageAwareWorkforceService:
    """
    Lọc và xếp hạng Agent Roster theo COSA Stage Policy.

    Sử dụng ManagementPolicyEngine để đọc priority_agents và deemphasized_tools
    của stage hiện tại, sau đó tính fit_score + priority + is_locked cho từng agent.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stage_roster(
        self,
        stage_code: str,
        workspace_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lấy Agent Roster đầy đủ được xếp hạng theo stage.

        Args:
            stage_code: Mã stage, ví dụ 'S0', 'S2', 'S3' hoặc enum string 'S2_SOLUTION_VALIDATION'
            workspace_id: ID workspace (None = global)

        Returns:
            Danh sách agent dict đã được enrich với priority, fit_score, is_locked,
            sắp xếp theo fit_score giảm dần (HIGH priority lên đầu).
        """
        # 1. Resolve stage policy
        stage_enum = self._resolve_stage_enum(stage_code)
        policy = ManagementPolicyEngine.get_policy(stage_enum)

        # 2. Lấy tất cả agents từ DB
        stmt = select(AgentDefinition)
        if workspace_id is not None:
            stmt = stmt.where(AgentDefinition.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        agents: List[AgentDefinition] = list(res.scalars().all())

        # 3. Import manifest để biết is_system
        try:
            from workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS
            manifest_map = {m["key"]: m for m in DEFAULT_AGENT_MANIFESTS}
        except Exception:
            manifest_map = {}

        # 4. Tính fit_score cho từng agent
        priority_agent_keys = {
            _PRIORITY_NAME_TO_KEY.get(name, name.lower().replace(" ", "_"))
            for name in policy.priority_agents
        }
        deemphasized = set(policy.deemphasized_tools)

        result = []
        for agent in agents:
            fit = self._compute_fit(
                agent_key=agent.key,
                agent_name=agent.name,
                priority_agent_keys=priority_agent_keys,
                deemphasized_tools=deemphasized,
                policy_priority_agents=policy.priority_agents,
            )
            is_system = (agent.key in manifest_map) and (not agent.config_jsonb.get("cloned_from"))
            default_tools = manifest_map.get(agent.key, {}).get("tools", [])
            custom_tools = agent.config_jsonb.get("custom_tools", []) if agent.config_jsonb else []
            tools = list(set(default_tools + custom_tools))

            result.append({
                "id": agent.id,
                "workspace_id": agent.workspace_id,
                "key": agent.key,
                "name": agent.name,
                "role_title": agent.role_title,
                "department": agent.department,
                "description": agent.description,
                "agent_type": agent.agent_type,
                "default_model_profile": agent.default_model_profile,
                "risk_level": agent.risk_level,
                "status": agent.status,
                "enabled": agent.enabled,
                "is_system": is_system,
                "tools": tools,
                "skills": agent.config_jsonb.get("skills", []) if agent.config_jsonb else [],
                # Stage-fit metadata
                "priority": fit["priority"],
                "fit_score": fit["fit_score"],
                "is_locked": fit["is_locked"],
                "stage_recommendation": fit["stage_recommendation"],
                "stage_code": policy.code,
                "stage_name_vi": policy.stage_name_vi,
            })

        # 5. Sắp xếp: HIGH priority → MEDIUM → LOW (locked ở cuối)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        result.sort(key=lambda a: (priority_order.get(a["priority"], 9), -a["fit_score"]))

        return result

    async def check_stage_fit(
        self,
        agent_key: str,
        stage_code: str,
        workspace_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Kiểm tra mức độ phù hợp của một agent cụ thể với stage.

        Returns dict: priority, fit_score, is_locked, stage_recommendation
        """
        stage_enum = self._resolve_stage_enum(stage_code)
        policy = ManagementPolicyEngine.get_policy(stage_enum)

        priority_agent_keys = {
            _PRIORITY_NAME_TO_KEY.get(name, name.lower().replace(" ", "_"))
            for name in policy.priority_agents
        }
        deemphasized = set(policy.deemphasized_tools)

        # Tìm agent name từ DB nếu cần
        agent_name = agent_key
        if workspace_id is not None:
            stmt = select(AgentDefinition).where(
                AgentDefinition.key == agent_key,
                AgentDefinition.workspace_id == workspace_id,
            )
            res = await self.db.execute(stmt)
            agent = res.scalars().first()
            if agent:
                agent_name = agent.name

        fit = self._compute_fit(
            agent_key=agent_key,
            agent_name=agent_name,
            priority_agent_keys=priority_agent_keys,
            deemphasized_tools=deemphasized,
            policy_priority_agents=policy.priority_agents,
        )
        fit["stage_code"] = policy.code
        fit["stage_name_vi"] = policy.stage_name_vi
        return fit

    def get_stage_summary(self, stage_code: str) -> Dict[str, Any]:
        """Lấy tóm tắt stage policy (không cần DB)."""
        stage_enum = self._resolve_stage_enum(stage_code)
        policy = ManagementPolicyEngine.get_policy(stage_enum)
        return {
            "stage_code": policy.code,
            "stage_name_vi": policy.stage_name_vi,
            "primary_goal": policy.primary_goal,
            "priority_agents": policy.priority_agents,
            "deemphasized_tools": policy.deemphasized_tools,
            "recommended_methods": policy.recommended_methods,
            "review_cadence": policy.review_cadence,
        }

    # --- Private helpers ---

    def _resolve_stage_enum(self, stage_code: str) -> ProjectStageEnum:
        """Chuyển đổi nhiều dạng stage code về ProjectStageEnum."""
        # Nếu là 'S0', 'S1', ..., 'S6' thì map sang enum
        short_code_map = {
            "S0": ProjectStageEnum.S0_EXPLORE,
            "S1": ProjectStageEnum.S1_PROBLEM_VALIDATION,
            "S2": ProjectStageEnum.S2_SOLUTION_VALIDATION,
            "S3": ProjectStageEnum.S3_BUSINESS_VALIDATION,
            "S4": ProjectStageEnum.S4_GO_TO_MARKET,
            "S5": ProjectStageEnum.S5_OPERATE_GROWTH,
            "S6": ProjectStageEnum.S6_SCALE_GOVERN,
        }
        if stage_code.upper() in short_code_map:
            return short_code_map[stage_code.upper()]
        # Thử parse trực tiếp enum string
        try:
            return ProjectStageEnum(stage_code)
        except ValueError:
            return ProjectStageEnum.S1_PROBLEM_VALIDATION

    def _compute_fit(
        self,
        agent_key: str,
        agent_name: str,
        priority_agent_keys: set,
        deemphasized_tools: set,
        policy_priority_agents: List[str],
    ) -> Dict[str, Any]:
        """
        Tính fit_score và priority cho một agent dựa trên policy.

        Thứ tự ưu tiên kiểm tra:
        1. Nếu agent key nằm trong priority_agent_keys → HIGH, fit 90–100
        2. Nếu agent name match priority_agents name → HIGH, fit 90–100
        3. Nếu agent domains giao với deemphasized_tools → LOW, is_locked, fit 0–20
        4. Còn lại → MEDIUM, fit 40–70
        """
        # Exec/Orchestrator luôn MEDIUM (không lock, không ưu tiên đặc biệt)
        if agent_key in ("founder_copilot", "general"):
            return {
                "priority": "MEDIUM",
                "fit_score": 60,
                "is_locked": False,
                "stage_recommendation": "Luôn khả dụng — Điều phối và hỗ trợ chung",
            }

        # Check priority: bằng key hoặc bằng tên
        is_priority_by_key = agent_key in priority_agent_keys
        is_priority_by_name = any(
            pa.lower() in agent_name.lower() or agent_name.lower() in pa.lower()
            for pa in policy_priority_agents
        )

        if is_priority_by_key or is_priority_by_name:
            # Tìm tên ưu tiên để lấy thứ hạng chính xác
            rank_bonus = 0
            for i, pa in enumerate(policy_priority_agents):
                if pa.lower() in agent_name.lower() or agent_name.lower() in pa.lower():
                    rank_bonus = max(0, 10 - i * 2)  # Agent đầu tiên trong list bonus cao nhất
                    break
                if _PRIORITY_NAME_TO_KEY.get(pa) == agent_key:
                    rank_bonus = max(0, 10 - i * 2)
                    break
            fit_score = min(100, 90 + rank_bonus)
            priority_names_str = ", ".join(policy_priority_agents)
            return {
                "priority": "HIGH",
                "fit_score": fit_score,
                "is_locked": False,
                "stage_recommendation": f"Agent ưu tiên cho giai đoạn này ({priority_names_str})",
            }

        # Check locked: agent domains giao với deemphasized_tools
        agent_domains = _AGENT_DOMAIN_MAP.get(agent_key, [])
        overlapping = deemphasized_tools.intersection(set(agent_domains))

        if overlapping:
            locked_domains = ", ".join(sorted(overlapping))
            return {
                "priority": "LOW",
                "fit_score": 10,
                "is_locked": True,
                "stage_recommendation": (
                    f"Không phù hợp với giai đoạn này — "
                    f"Các domain '{locked_domains}' bị deemphasized theo Stage Policy"
                ),
            }

        # MEDIUM: không ưu tiên, không lock
        return {
            "priority": "MEDIUM",
            "fit_score": 50,
            "is_locked": False,
            "stage_recommendation": "Sẵn sàng hỗ trợ — Không phải agent ưu tiên chính cho giai đoạn này",
        }
