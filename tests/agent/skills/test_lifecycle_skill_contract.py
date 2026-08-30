from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.skills.contracts import (
    AutonomyPolicy,
    EvidenceRequirement,
    LifecycleApplicability,
    ProjectLifecycleStage,
    SkillQualitySpec,
    SkillSpec,
    SkillStatus,
)


def test_skillspec_hash_includes_lifecycle_governance():
    base = SkillSpec(
        id="lifecycle.context-resolver",
        version="1.0.0",
        instructions="Resolve context for project.",
        applicability=LifecycleApplicability(project_stages=[ProjectLifecycleStage.P0_DISCOVERY]),
        autonomy=AutonomyPolicy(ceiling="L0_OBSERVE", side_effect_class="R"),
        evidence_requirement=EvidenceRequirement(min_source_refs=0, self_validation_forbidden=True),
        quality=SkillQualitySpec(
            eval_suite="evals/lifecycle/context-resolver.yaml",
            required_negative_cases=["missing-workspace", "cross-workspace"],
        ),
    )
    base_hash = base.compute_hash()

    # 1. Changing project_stages changes definition hash
    changed_stage = base.model_copy(
        update={
            "applicability": LifecycleApplicability(
                project_stages=[ProjectLifecycleStage.P1_PROBLEM_VALIDATION]
            )
        }
    )
    assert base_hash != changed_stage.compute_hash()

    # 2. Changing autonomy ceiling changes definition hash
    changed_autonomy = base.model_copy(
        update={"autonomy": AutonomyPolicy(ceiling="L1_PROPOSE", side_effect_class="A")}
    )
    assert base_hash != changed_autonomy.compute_hash()

    # 3. Changing evidence requirement changes definition hash
    changed_evidence = base.model_copy(
        update={
            "evidence_requirement": EvidenceRequirement(
                min_source_refs=2, freshness_days=30, self_validation_forbidden=True
            )
        }
    )
    assert base_hash != changed_evidence.compute_hash()

    # 4. Changing quality spec changes definition hash
    changed_quality = base.model_copy(
        update={
            "quality": SkillQualitySpec(
                eval_suite="evals/lifecycle/context-resolver.yaml",
                required_negative_cases=["missing-workspace", "cross-workspace", "tampered-claim"],
            )
        }
    )
    assert base_hash != changed_quality.compute_hash()

    # 5. Same content produces exact same hash (deterministic)
    clone = SkillSpec(
        id="lifecycle.context-resolver",
        version="1.0.0",
        instructions="Resolve context for project.",
        applicability=LifecycleApplicability(project_stages=[ProjectLifecycleStage.P0_DISCOVERY]),
        autonomy=AutonomyPolicy(ceiling="L0_OBSERVE", side_effect_class="R"),
        evidence_requirement=EvidenceRequirement(min_source_refs=0, self_validation_forbidden=True),
        quality=SkillQualitySpec(
            eval_suite="evals/lifecycle/context-resolver.yaml",
            required_negative_cases=["missing-workspace", "cross-workspace"],
        ),
    )
    assert base_hash == clone.compute_hash()


def test_skillspec_invalid_governance_values_fail_validation():
    # Invalid project stage
    with pytest.raises(ValidationError):
        LifecycleApplicability(project_stages=["P8_UNKNOWN"])  # type: ignore

    # Invalid autonomy ceiling
    with pytest.raises(ValidationError):
        AutonomyPolicy(ceiling="L3_UNBOUNDED")  # type: ignore

    # Invalid evidence freshness
    with pytest.raises(ValidationError):
        EvidenceRequirement(freshness_days=0)

    # Empty eval suite
    with pytest.raises(ValidationError):
        SkillQualitySpec(eval_suite="", required_negative_cases=["test"])

    # Empty negative cases
    with pytest.raises(ValidationError):
        SkillQualitySpec(eval_suite="suite.yaml", required_negative_cases=[])
