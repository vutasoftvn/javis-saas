from unittest.mock import MagicMock
import pytest

from app.db.models import Brain, WorkspaceMember
from app.core.snowflake import generate_snowflake_id
from app.business.marketing.models import MarketingExperiment
from app.business.marketing.models_validation import (
    Assumption,
    AssumptionCategory,
    AssumptionStatus,
    ConfidenceLevel,
)
from app.business.marketing.schemas.marketing_schemas import ExperimentCreate
from app.business.marketing.schemas.validation_schemas import (
    AIDesignExperimentRequest,
    ScaleWarningCheckRequest,
    CompleteValidationExperimentRequest,
)
from app.business.marketing.services.experiment_designer_service import ExperimentDesignerService
from app.business.marketing.routers.campaign_router import create_experiment
from app.business.marketing.routers.validation_router import (
    design_experiment_ai,
    check_scale_warning,
    complete_validation_experiment,
)
from app.tests.marketing_fakes import FakeDb


def mock_member(ws_id: int) -> WorkspaceMember:
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = generate_snowflake_id()
    m.workspace_id = ws_id
    m.role = "admin"
    return m


@pytest.fixture
def scope():
    ws_id = generate_snowflake_id()
    brain = Brain(id=generate_snowflake_id(), workspace_id=ws_id)
    return ws_id, brain, mock_member(ws_id)


# ===================================================================
# 1. AI Experiment Designer (§27 in E3.md)
# ===================================================================

def test_design_smallest_experiment_for_customer_problem():
    res = ExperimentDesignerService.design_smallest_experiment(
        assumption_statement="Chủ homestay cần công cụ AI tự động đăng bài",
        category="problem",
        impact=5,
        uncertainty=5,
    )
    assert res["method"] == "interview"
    assert ">= 60%" in res["success_threshold"]
    assert res["cost_estimate"] == 0.0
    assert res["requires_external_action"] is False


def test_design_smallest_experiment_for_pricing():
    res = ExperimentDesignerService.design_smallest_experiment(
        assumption_statement="Khách hàng chấp nhận trả 500k/tháng",
        category="pricing",
        impact=5,
        uncertainty=5,
    )
    assert res["method"] == "pricing_test"
    assert "intent" in res["metric"]
    assert res["requires_external_action"] is True
    assert res["cost_estimate"] > 0


# ===================================================================
# 2. Scale Warning Evaluation (§30, §52 in E3.md)
# ===================================================================

def test_scale_warning_on_untested_critical_assumption(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Khách hàng sẵn sàng chi trả 50 triệu",
        impact=5,
        uncertainty=5,
        criticality=25,
        status=AssumptionStatus.UNTESTED.value,
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    payload = ScaleWarningCheckRequest(assumption_id=asm.id)
    check_res = check_scale_warning(payload=payload, member=member, db=db)

    assert check_res["has_warning"] is True
    assert check_res["allow_scale"] is True  # Soft warning, does not block
    assert check_res["recommendation"] == "EXPERIMENT"
    assert "Continue Anyway" in check_res["options"]


def test_no_warning_when_assumption_is_supported(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Khách hàng có nỗi đau",
        impact=5,
        uncertainty=2,
        criticality=10,
        status=AssumptionStatus.SUPPORTED.value,
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    payload = ScaleWarningCheckRequest(assumption_id=asm.id)
    check_res = check_scale_warning(payload=payload, member=member, db=db)

    assert check_res["has_warning"] is False
    assert check_res["recommendation"] == "CAMPAIGN"


# ===================================================================
# 3. Create Validation Experiment & Complete Lifecycle (§25, §102)
# ===================================================================

def test_create_validation_experiment_linked_to_assumption(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="SME Founder needs AI",
        impact=5,
        uncertainty=5,
        criticality=25,
        status=AssumptionStatus.UNTESTED.value,
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    payload = ExperimentCreate(
        assumption_id=asm.id,
        hypothesis="10 founders confirm problem",
        method="interview",
        metric="problem_confirmation_rate",
        success_threshold=">= 60%",
        minimum_sample=10,
        timebox_days=5,
    )
    res = create_experiment(payload=payload, workspace_id=ws_id, brain_id=brain.id, member=member, db=db)
    exp_data = res["experiment"]

    assert exp_data["assumption_id"] == str(asm.id)
    assert exp_data["method"] == "interview"
    assert exp_data["success_threshold"] == ">= 60%"
    assert exp_data["status"] == "running"


def test_complete_experiment_updates_assumption_and_creates_evidence(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="SME Founder needs AI",
        impact=5,
        uncertainty=5,
        criticality=25,
        status=AssumptionStatus.TESTING.value,
        evidence_ids=[],
    )
    exp = MarketingExperiment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        assumption_id=asm.id,
        hypothesis="10 founders confirm problem",
        metric="problem_confirmation_rate",
        status="running",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm], MarketingExperiment: [exp]})

    complete_payload = CompleteValidationExperimentRequest(
        conclusion="supported",
        observations={"confirmed_count": 8, "sample_size": 10},
        learning_summary="8/10 founder xác nhận context fragmentation là nỗi đau lớn nhất.",
    )
    res = complete_validation_experiment(
        experiment_id=exp.id,
        payload=complete_payload,
        brain_id=brain.id,
        member=member,
        db=db,
    )

    assert res["status"] == "completed"
    assert res["conclusion"] == "supported"
    assert res["evidence_id"] is not None
    assert res["assumption_status"] == AssumptionStatus.SUPPORTED.value
    assert res["assumption_confidence"] == ConfidenceLevel.HIGH.value
    # Verify underlying assumption object
    assert asm.status == AssumptionStatus.SUPPORTED.value
    assert len(asm.evidence_ids) >= 1
