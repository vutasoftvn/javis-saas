"""Offline Evaluation Runner for benchmarking and validating AI programs."""

import logging
from typing import Any, Dict, List
from app.ai.programs.schemas import AIProgramRequest
from app.ai.programs.registry import AIProgramRegistry
from app.ai.programs.runtime import AIProgramRuntime, DSPyProgramRuntime
from app.ai.evaluation.metrics import AIProgramMetrics, MetricScore, ProgramEvaluationResult

logger = logging.getLogger(__name__)


class AIProgramEvaluator:
    """Evaluates AI programs on golden datasets."""

    def __init__(self, runtime: AIProgramRuntime | None = None) -> None:
        self.runtime = runtime or DSPyProgramRuntime()

    async def evaluate_case(
        self,
        program_key: str,
        case_input: Dict[str, Any],
        expected_output: Dict[str, Any] | None = None,
        workspace_id: str = "eval_workspace",
    ) -> ProgramEvaluationResult:
        """Run and score a single evaluation case."""
        request = AIProgramRequest(
            workspace_id=workspace_id,
            program_key=program_key,
            input=case_input,
        )
        result = await self.runtime.run(request)

        scores: List[MetricScore] = []
        hard_failed = False

        if result.status != "completed" or not result.output:
            scores.append(
                MetricScore(
                    metric_key="execution_status",
                    score=0.0,
                    weight=1.0,
                    passed=False,
                    hard_fail=True,
                    feedback=f"Execution status: {result.status} ({result.error_message})",
                )
            )
            return ProgramEvaluationResult(
                program_key=program_key,
                program_version=result.program_version,
                composite_score=0.0,
                hard_failed=True,
                scores=scores,
                case_count=1,
            )

        output = result.output

        # Domain-specific evaluation logic
        if program_key == "ceo.brief":
            # 1. Schema validity
            req_fields = ["headline", "wins", "risks", "today_top_3"]
            s1 = AIProgramMetrics.evaluate_schema_validity(output, req_fields)
            scores.append(s1)
            if s1.hard_fail:
                hard_failed = True

            # 2. Brevity
            s2 = AIProgramMetrics.evaluate_brevity_and_focus(output.get("today_top_3", []), max_items=3)
            scores.append(s2)

        elif program_key == "sales.lead_qualification":
            # 1. Schema validity
            req_fields = ["fit_score", "need_score", "timing_score", "recommended_stage", "recommended_next_action"]
            s1 = AIProgramMetrics.evaluate_schema_validity(output, req_fields)
            scores.append(s1)
            if s1.hard_fail:
                hard_failed = True

            # 2. Calibration of fit score
            s2 = AIProgramMetrics.evaluate_score_calibration(output.get("fit_score", -1.0))
            scores.append(s2)
            if s2.hard_fail:
                hard_failed = True

            # 3. Evidence grounding
            s3 = AIProgramMetrics.evaluate_evidence_grounding(output.get("evidence", []))
            scores.append(s3)

        # Compute weighted composite score
        total_weight = sum(s.weight for s in scores) or 1.0
        weighted_sum = sum(s.score * s.weight for s in scores)
        composite = 0.0 if hard_failed else round(weighted_sum / total_weight, 4)

        return ProgramEvaluationResult(
            program_key=program_key,
            program_version=result.program_version,
            composite_score=composite,
            hard_failed=hard_failed,
            scores=scores,
            case_count=1,
        )

    async def evaluate_dataset(
        self,
        program_key: str,
        cases: List[Dict[str, Any]],
        workspace_id: str = "eval_workspace",
    ) -> ProgramEvaluationResult:
        """Run evaluation over a dataset batch and aggregate results."""
        if not cases:
            return ProgramEvaluationResult(
                program_key=program_key,
                program_version="1.0.0",
                composite_score=1.0,
                hard_failed=False,
                scores=[],
                case_count=0,
            )

        all_scores: List[MetricScore] = []
        composite_sum = 0.0
        any_hard_failed = False
        version = "1.0.0"

        for case in cases:
            case_res = await self.evaluate_case(
                program_key=program_key,
                case_input=case.get("input", {}),
                expected_output=case.get("expected"),
                workspace_id=workspace_id,
            )
            version = case_res.program_version
            if case_res.hard_failed:
                any_hard_failed = True
            composite_sum += case_res.composite_score
            all_scores.extend(case_res.scores)

        avg_composite = round(composite_sum / len(cases), 4)

        return ProgramEvaluationResult(
            program_key=program_key,
            program_version=version,
            composite_score=avg_composite,
            hard_failed=any_hard_failed,
            scores=all_scores,
            case_count=len(cases),
        )
