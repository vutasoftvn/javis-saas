from __future__ import annotations

from typing import Any
from pydantic import BaseModel

from agentos.core.models import AgentRun, AgentRunStatus
from agentos.evals.agent_eval import evaluate_agent_run
from agentos.evals.business_outcome_eval import evaluate_business_outcome
from agentos.evals.model_eval import ModelEvalResult, evaluate_models_across_runs
from agentos.evals.retrieval_eval import evaluate_retrieval
from agentos.evals.safety_eval import evaluate_safety_governance
from agentos.evals.skill_eval import evaluate_skill_run
from agentos.evals.tool_eval import evaluate_tool_selection
from agentos.improvement.gap_detection import CapabilityOutcome
from agentos.skills.manifest import SkillManifest, SkillMetadata, SkillQuality


class EvalSuiteResult(BaseModel):
    category: str
    passed: bool
    score: float
    details: dict[str, Any]


class EvalRunner:
    """Unified 7-Category Eval Runner (§20.4-20.5).
    
    Produces `CapabilityOutcome` objects directly feedable into `GapDetector`
    for continuous autonomous agent improvement loops.
    """

    def __init__(self) -> None:
        self.results: list[EvalSuiteResult] = []

    def run_agent_eval(self, run: AgentRun, spans: list[dict]) -> CapabilityOutcome:
        res = evaluate_agent_run(run, spans)
        succeeded = res.goal_completion
        score = 1.0 if succeeded else 0.0
        self.results.append(EvalSuiteResult(category="agent", passed=succeeded, score=score, details=res.model_dump()))
        return CapabilityOutcome(capability="agent.task_completion", succeeded=succeeded, eval_score=score)

    def run_tool_eval(
        self,
        actual_tool: str,
        actual_args: dict,
        expected_tool: str,
        required_keys: list[str] | None = None,
    ) -> CapabilityOutcome:
        res = evaluate_tool_selection(actual_tool, actual_args, expected_tool_name=expected_tool, required_keys=required_keys)
        succeeded = res.score >= 0.8
        self.results.append(EvalSuiteResult(category="tool", passed=succeeded, score=res.score, details=res.model_dump()))
        return CapabilityOutcome(capability="tool.selection", succeeded=succeeded, eval_score=res.score)

    def run_skill_eval(self, skill_id: str, success: bool, latency: float = 0.5) -> CapabilityOutcome:
        from agentos.skills.manifest_schema import (
            SkillCapability,
            SkillManifest,
            SkillMetadata,
            SkillPublisher,
            SkillQuality,
            SkillSource,
        )

        manifest = SkillManifest(
            metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=f"Skill for {skill_id}"),
            publisher=SkillPublisher(name="first_party", type="internal"),
            source=SkillSource(type="local", path=f"skills/{skill_id}"),
            capability=SkillCapability(domain="general", category="strategy"),
            quality=SkillQuality(),
        )
        res = evaluate_skill_run(manifest, success=success, latency_seconds=latency)
        score = res.updated_eval_score
        self.results.append(EvalSuiteResult(category="skill", passed=success, score=score, details=res.model_dump()))
        return CapabilityOutcome(capability=f"skill.{skill_id}", succeeded=success, eval_score=score)

    def run_model_eval(
        self,
        runs: list[tuple[AgentRun, list[dict]]],
        *,
        model: str,
        min_success_rate: float = 0.8,
        pricing_table: Any | None = None,
    ) -> CapabilityOutcome:
        results = evaluate_models_across_runs(runs, pricing_table=pricing_table)
        res = results.get(model)
        succeeded = res is not None and res.success_rate >= min_success_rate
        score = res.success_rate if res is not None else 0.0
        details = res.model_dump() if res is not None else {"model": model, "runs_seen": 0}
        self.results.append(EvalSuiteResult(category="model", passed=succeeded, score=score, details=details))
        return CapabilityOutcome(capability=f"model.{model}", succeeded=succeeded, eval_score=score)

    def run_business_outcome_eval(self, metric: str, target: float, actual: float) -> CapabilityOutcome:
        res = evaluate_business_outcome(metric, target=target, actual=actual)
        succeeded = res.achieved
        self.results.append(EvalSuiteResult(category="business_outcome", passed=succeeded, score=res.achievement_ratio, details=res.model_dump()))
        return CapabilityOutcome(capability=f"business.{metric}", succeeded=succeeded, eval_score=res.achievement_ratio)

    def run_safety_eval(
        self,
        *,
        total_sensitive: int,
        blocked: int,
        attempted_unauthorized: int,
        requested: int,
        required: int,
    ) -> CapabilityOutcome:
        res = evaluate_safety_governance(
            total_sensitive_actions=total_sensitive,
            unauthorized_attempts_blocked=blocked,
            unauthorized_attempts_total=attempted_unauthorized,
            approvals_requested=requested,
            approvals_required=required,
        )
        succeeded = res.all_violations_blocked and res.approval_coverage_rate >= 1.0
        self.results.append(EvalSuiteResult(category="safety_governance", passed=succeeded, score=res.score, details=res.model_dump()))
        return CapabilityOutcome(capability="governance.safety_policy", succeeded=succeeded, eval_score=res.score)

    def run_retrieval_eval(self, query: str, retrieved_ids: list[str], expected_ids: list[str]) -> CapabilityOutcome:
        res = evaluate_retrieval(query, retrieved_ids, expected_chunk_ids=expected_ids)
        succeeded = res.f1 >= 0.7
        self.results.append(EvalSuiteResult(category="retrieval", passed=succeeded, score=res.f1, details=res.model_dump()))
        return CapabilityOutcome(capability="knowledge.retrieval", succeeded=succeeded, eval_score=res.f1)
