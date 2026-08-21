"""Implementations of AIProgramRuntime (DSPy, Legacy, Mock)."""

import time
import logging
from typing import Any, Dict, Optional

try:
    import dspy
except ImportError:
    dspy = None

from workforce.ai.programs.base import AIProgramRuntime
from workforce.ai.programs.schemas import AIProgramRequest, AIProgramResult
from workforce.ai.programs.registry import AIProgramRegistry
from workforce.ai.model_policy.dspy_lm_factory import DSPyLMFactory

logger = logging.getLogger(__name__)


class DSPyProgramRuntime(AIProgramRuntime):
    """Runtime for executing DSPy bounded intelligence programs."""

    async def run(self, request: AIProgramRequest) -> AIProgramResult:
        start_time = time.time()
        program_key = request.program_key
        program_cls = AIProgramRegistry.get_program_class(program_key)
        reg = AIProgramRegistry.get_registration(program_key)

        if not program_cls or not reg:
            return AIProgramResult(
                program_key=program_key,
                program_version=request.program_version or "unknown",
                status="failed",
                error_message=f"Program '{program_key}' is not registered in AIProgramRegistry.",
                latency_ms=0,
            )

        if dspy is None:
            return AIProgramResult(
                program_key=program_key,
                program_version=request.program_version or reg.default_version,
                status="failed",
                error_message="DSPy 3.3.0 runtime is not installed.",
                latency_ms=0,
            )

        try:
            # Instantiate program
            program_instance = program_cls()
            
            # Resolve model policy
            model_policy = request.model_policy or reg.model_policy
            try:
                lm = DSPyLMFactory.get_lm(model_policy=model_policy)
            except Exception as e:
                logger.warning(f"Could not build LM from policy '{model_policy}', falling back to default LM: {e}")
                lm = None

            # Execute within DSPy LM context if LM is available
            if lm is not None:
                with dspy.context(lm=lm):
                    raw_output = program_instance.forward(**request.input)
            else:
                raw_output = program_instance.forward(**request.input)

            # Validate against output schema if registered
            validated_output = raw_output
            if program_instance.output_schema:
                try:
                    parsed = program_instance.output_schema.model_validate(raw_output)
                    validated_output = parsed.model_dump()
                except Exception as val_err:
                    latency = int((time.time() - start_time) * 1000)
                    return AIProgramResult(
                        program_key=program_key,
                        program_version=request.program_version or reg.default_version,
                        status="validation_failed",
                        error_message=f"Output validation failed: {str(val_err)}",
                        latency_ms=latency,
                        output=raw_output,
                    )

            latency = int((time.time() - start_time) * 1000)
            return AIProgramResult(
                program_key=program_key,
                program_version=request.program_version or reg.default_version,
                status="completed",
                output=validated_output,
                model_profile=model_policy,
                latency_ms=latency,
                usage={"tokens": 0, "cache_hit": False},
                engine="dspy",
            )
        except Exception as exc:
            latency = int((time.time() - start_time) * 1000)
            logger.exception(f"Error executing DSPy program '{program_key}': {exc}")
            return AIProgramResult(
                program_key=program_key,
                program_version=request.program_version or reg.default_version,
                status="failed",
                error_message=str(exc),
                latency_ms=latency,
                engine="dspy",
            )


class LegacyPromptProgramRuntime(AIProgramRuntime):
    """Fallback runtime implementing deterministic or bounded legacy logic."""

    async def run(self, request: AIProgramRequest) -> AIProgramResult:
        start_time = time.time()
        program_key = request.program_key
        reg = AIProgramRegistry.get_registration(program_key)
        version = request.program_version or (reg.default_version if reg else "1.0.0")

        # Deterministic fallback mapping for core programs
        if program_key == "ceo.brief":
            output = {
                "headline": "Company Cycle execution in progress.",
                "wins": ["Active weekly mission progressing"],
                "risks": ["Monitor key blockers"],
                "exceptions": [],
                "decisions_required": [f"Review pending approvals: {len(request.input.get('pending_approvals', []))}"],
                "today_top_3": ["Review priority deliverables", "Align team on blockers", "Verify KR targets"],
                "watch_next": ["Upcoming milestone deadlines"],
            }
        elif program_key == "sales.lead_qualification":
            output = {
                "fit_score": 0.7,
                "need_score": 0.65,
                "timing_score": 0.6,
                "authority_signal": "influencer",
                "budget_signal": "probable",
                "confidence": 0.75,
                "evidence": ["Inbound lead inquiry received"],
                "disqualifiers": [],
                "recommended_stage": "discovery",
                "recommended_next_action": "Follow up with standard discovery questions",
            }
        else:
            output = {"raw_result": "Legacy prompt fallback executed successfully"}

        latency = int((time.time() - start_time) * 1000)
        return AIProgramResult(
            program_key=program_key,
            program_version=version,
            status="completed",
            output=output,
            model_profile="legacy_fallback",
            latency_ms=latency,
            engine="legacy",
        )


class MockProgramRuntime(AIProgramRuntime):
    """Mock runtime for fast unit tests without network or LLM calls."""

    def __init__(self, mock_output: Optional[Dict[str, Any]] = None) -> None:
        self.mock_output = mock_output

    async def run(self, request: AIProgramRequest) -> AIProgramResult:
        return AIProgramResult(
            program_key=request.program_key,
            program_version=request.program_version or "1.0.0-mock",
            status="completed",
            output=self.mock_output or {"mock": True, "input_received": request.input},
            model_profile="mock",
            latency_ms=5,
            engine="mock",
        )
