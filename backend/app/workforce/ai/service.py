"""AI Program Service: Central orchestration and gateway for AI reasoning programs."""

import os
import logging
from typing import Any, Dict, Optional

from app.workforce.ai.programs.schemas import AIProgramRequest, AIProgramResult
from app.workforce.ai.programs.registry import AIProgramRegistry
from app.workforce.ai.programs.runtime import (
    AIProgramRuntime,
    DSPyProgramRuntime,
    LegacyPromptProgramRuntime,
)

logger = logging.getLogger(__name__)


class AIProgramService:
    """Service gateway for invoking bounded AI programs across COSA OS."""

    def __init__(
        self,
        dspy_runtime: Optional[AIProgramRuntime] = None,
        fallback_runtime: Optional[AIProgramRuntime] = None,
    ) -> None:
        self.dspy_runtime = dspy_runtime or DSPyProgramRuntime()
        self.fallback_runtime = fallback_runtime or LegacyPromptProgramRuntime()

    def is_dspy_globally_enabled(self) -> bool:
        """Check if DSPy is enabled globally via environment / feature flags."""
        val = os.getenv("COSA_DSPY_ENABLED", "true").lower()
        return val in ("true", "1", "yes", "on")

    def is_program_dspy_enabled(self, program_key: str) -> bool:
        """Check per-program DSPy enablement."""
        if not self.is_dspy_globally_enabled():
            return False

        # Check specific override env var, e.g. COSA_DSPY_CEO_BRIEF=true
        env_var_name = f"COSA_DSPY_{program_key.upper().replace('.', '_')}"
        if env_var_name in os.environ:
            val = os.getenv(env_var_name, "true").lower()
            return val in ("true", "1", "yes", "on")

        # Default enabled if globally enabled
        return True

    async def run_program(self, request: AIProgramRequest) -> AIProgramResult:
        """Execute the AI program with appropriate runtime and fallback strategy."""
        program_key = request.program_key
        reg = AIProgramRegistry.get_registration(program_key)

        if not reg:
            return AIProgramResult(
                program_key=program_key,
                program_version=request.program_version or "unknown",
                status="failed",
                error_message=f"Program key '{program_key}' is not registered.",
                latency_ms=0,
            )

        # Decide runtime
        use_dspy = self.is_program_dspy_enabled(program_key)
        
        if use_dspy:
            result = await self.dspy_runtime.run(request)
            # If DSPy run succeeded, return
            if result.status == "completed":
                return result
            
            # If DSPy failed, evaluate fallback policy
            logger.warning(
                f"DSPy execution failed for '{program_key}' (error: {result.error_message}). "
                f"Evaluating fallback policy '{reg.fallback_mode}'..."
            )
            if reg.fallback_mode == "fail_closed":
                return result

        # Fallback to legacy runtime
        logger.info(f"Invoking Legacy fallback runtime for program '{program_key}'")
        return await self.fallback_runtime.run(request)


# Singleton instance for standard use
ai_program_service = AIProgramService()
