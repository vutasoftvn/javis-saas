"""COSA AI Program Registry with boundary checks and schema validations."""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from app.workforce.ai.programs.base import BaseCOSAProgram
from app.workforce.ai.programs.ceo_brief.program import CEOBriefProgram
from app.workforce.ai.programs.sales.lead_qualification import LeadQualificationProgram


# Forbidden module keys from V13 Focused Company Cycle OS
FORBIDDEN_PROGRAM_PREFIXES = (
    "strategy.pestel",
    "strategy.swot",
    "strategy.tows",
    "strategy.bsc",
    "strategy.portfolio",
    "pestel.",
    "swot.",
    "tows.",
    "bsc.",
    "portfolio_strategy.",
)


class ProgramRegistration(BaseModel):
    """Metadata describing a registered AI program."""

    key: str
    name: str
    domain: str
    description: str
    program_class_path: str
    default_version: str = "1.0.0"
    enabled: bool = True
    engine: str = "dspy"
    model_policy: str = "fast_reasoning"
    timeout_seconds: int = 30
    fallback_mode: str = "legacy"  # "legacy" or "fail_closed"
    allowed_context: List[str] = []
    forbidden_context: List[str] = ["raw_credentials", "cross_tenant_data"]


class AIProgramRegistry:
    """Central registry for COSA Bounded Intelligence Programs."""

    _programs: Dict[str, Type[BaseCOSAProgram]] = {}
    _registrations: Dict[str, ProgramRegistration] = {}

    @classmethod
    def initialize_default_programs(cls) -> None:
        """Register default V13.1 / V13.2 approved programs."""
        cls._programs.clear()
        cls._registrations.clear()

        # 1. CEO Brief
        cls.register(
            key="ceo.brief",
            program_cls=CEOBriefProgram,
            meta=ProgramRegistration(
                key="ceo.brief",
                name="CEO Briefing Synthesis",
                domain="management",
                description="Synthesizes company cycle, KR deltas, and cross-domain signals into a daily executive brief",
                program_class_path="app.workforce.ai.programs.ceo_brief.program.CEOBriefProgram",
                default_version="1.0.0",
                fallback_mode="legacy",
            ),
        )

        # 2. Sales Lead Qualification
        cls.register(
            key="sales.lead_qualification",
            program_cls=LeadQualificationProgram,
            meta=ProgramRegistration(
                key="sales.lead_qualification",
                name="Sales Lead Qualification",
                domain="sales",
                description="Evaluates inbound leads against ICP criteria, scoring fit, need, and timing with evidence",
                program_class_path="app.workforce.ai.programs.sales.lead_qualification.LeadQualificationProgram",
                default_version="1.0.0",
                fallback_mode="legacy",
            ),
        )

    @classmethod
    def register(
        cls,
        key: str,
        program_cls: Type[BaseCOSAProgram],
        meta: ProgramRegistration,
    ) -> None:
        """Register an AI program after validating boundary rules."""
        # Enforce V13 Focused Company Cycle boundary rules
        for forbidden in FORBIDDEN_PROGRAM_PREFIXES:
            if key.startswith(forbidden):
                raise ValueError(
                    f"Registration rejected: Program key '{key}' is forbidden under V13 Focused Company Cycle OS. "
                    "Strategic frameworks (PESTEL, SWOT, TOWS, BSC) must remain disabled."
                )

        cls._programs[key] = program_cls
        cls._registrations[key] = meta

    @classmethod
    def get_program_class(cls, key: str) -> Optional[Type[BaseCOSAProgram]]:
        """Get program implementation class by key."""
        return cls._programs.get(key)

    @classmethod
    def get_registration(cls, key: str) -> Optional[ProgramRegistration]:
        """Get program registration metadata by key."""
        return cls._registrations.get(key)

    @classmethod
    def exists(cls, key: str) -> bool:
        """Check if program key is registered."""
        return key in cls._programs

    @classmethod
    def list_programs(cls) -> List[ProgramRegistration]:
        """List all active registered programs."""
        return list(cls._registrations.values())


# Auto-initialize defaults on import
AIProgramRegistry.initialize_default_programs()
