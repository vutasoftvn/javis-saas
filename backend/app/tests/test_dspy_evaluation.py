"""Unit tests for DSPy Evaluation and Metrics Engine."""

import pytest
from app.workforce.ai.evaluation.metrics import AIProgramMetrics
from app.workforce.ai.evaluation.evaluators import AIProgramEvaluator
from app.workforce.ai.optimization.artifacts import ProgramArtifactManifest, ProgramArtifactStore
from app.workforce.ai.optimization.gepa import GEPAOptimizationConfig, GEPAOptimizerRunner


def test_schema_validity_metric():
    """Test deterministic schema validity scoring."""
    valid_output = {"headline": "All good", "wins": ["Win 1"], "risks": []}
    score = AIProgramMetrics.evaluate_schema_validity(valid_output, ["headline", "wins"])
    assert score.passed is True
    assert score.score == 1.0
    assert score.hard_fail is False

    invalid_output = {"headline": "Only headline"}
    score_invalid = AIProgramMetrics.evaluate_schema_validity(invalid_output, ["headline", "wins"])
    assert score_invalid.passed is False
    assert score_invalid.score == 0.0
    assert score_invalid.hard_fail is True


def test_score_calibration_metric():
    """Test score calibration metric."""
    assert AIProgramMetrics.evaluate_score_calibration(0.85).passed is True
    assert AIProgramMetrics.evaluate_score_calibration(1.2).passed is False


@pytest.mark.asyncio
async def test_offline_evaluator_batch():
    """Test AIProgramEvaluator running evaluation on a batch."""
    from app.workforce.ai.programs.runtime import LegacyPromptProgramRuntime
    evaluator = AIProgramEvaluator(runtime=LegacyPromptProgramRuntime())
    cases = [
        {"input": {"lead": {"name": "Lead 1"}}, "expected": {}},
        {"input": {"lead": {"name": "Lead 2"}}, "expected": {}},
    ]
    res = await evaluator.evaluate_dataset("sales.lead_qualification", cases)
    assert res.program_key == "sales.lead_qualification"
    assert res.composite_score > 0.0
    assert res.case_count == 2
    assert res.hard_failed is False


@pytest.mark.asyncio
async def test_gepa_optimizer_runner(tmp_path):
    """Test GEPAOptimizerRunner creating immutable candidate artifact."""
    store = ProgramArtifactStore(base_dir=str(tmp_path))
    runner = GEPAOptimizerRunner(artifact_store=store)

    config = GEPAOptimizationConfig(
        program_key="ceo.brief",
        base_version="1.0.0",
        target_version="1.1.0",
    )
    val_cases = [{"input": {}}]
    opt_result = await runner.run_optimization(config, train_cases=[], val_cases=val_cases)

    assert opt_result.status == "completed"
    assert opt_result.improved is True
    assert opt_result.artifact_path is not None
    assert opt_result.artifact_hash is not None

    # Verify loaded state from disk
    loaded_state = store.load_artifact("ceo.brief", "1.1.0")
    assert loaded_state is not None
    assert loaded_state["version"] == "1.1.0"
