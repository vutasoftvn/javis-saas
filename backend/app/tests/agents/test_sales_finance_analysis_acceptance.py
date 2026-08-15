import pytest
from unittest.mock import MagicMock, patch

from app.agents.execution.analysis_service import DomainAnalysisService
from app.agents.execution.manager import execution_provider_manager
from app.agents.orchestration.chief_of_staff import ChiefOfStaffOrchestrator
from app.agents.runtime.adapters.mock import MockRuntime
from app.core.snowflake import generate_snowflake_id
from app.db.models import WorkspaceMember
from app.modules.sales.sales_tools import analyze_sales_data
from app.modules.finance.finance_tools import analyze_financial_data


SAMPLE_SALES_CSV = """deal_id,client_name,deal_value,stage
1,Cong ty Alpha,50000000,won
2,Tap doan Beta,100000000,won
3,Cong ty Gamma,30000000,lost
4,Doanh nghiep Delta,20000000,negotiation
"""

SAMPLE_FINANCE_CSV = """date,amount,type,category
2026-08-01,150000000,income,subscription
2026-08-02,40000000,expense,server
2026-08-03,30000000,expense,marketing
2026-08-04,10000000,expense,office
"""


from app.agents.execution.models import ExecutionJob


def _mock_db_with_session():
    db = MagicMock()
    stored_jobs = {}

    def mock_add(instance):
        if hasattr(instance, "id") and instance.id:
            stored_jobs[instance.id] = instance

    db.add.side_effect = mock_add

    def mock_query(model):
        q = MagicMock()
        def mock_filter(*args, **kwargs):
            fq = MagicMock()
            def mock_first():
                if model == ExecutionJob and stored_jobs:
                    # Return latest added job
                    return list(stored_jobs.values())[-1]
                return None
            fq.first.side_effect = mock_first
            fq.all.return_value = []
            return fq
        q.filter.side_effect = mock_filter
        return q

    db.query.side_effect = mock_query
    return db


@pytest.mark.asyncio
async def test_sales_analysis_job_acceptance_flow():
    """Acceptance test §52: Upload sales.csv -> run sandbox -> collect artifacts -> destroy -> audit."""
    await execution_provider_manager.start()

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    db = _mock_db_with_session()

    with patch("app.agents.execution.artifacts.put_object") as mock_put:
        result = await DomainAnalysisService.run_sales_analysis_now(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            csv_content=SAMPLE_SALES_CSV,
            agent_run_id=run_id,
            provider="mock",
        )

    assert result.status.value in ["completed", "queued"]
    assert result.provider == "mock"
    assert db.add.called
    assert db.commit.called


@pytest.mark.asyncio
async def test_finance_analysis_job_acceptance_flow():
    """Acceptance test for Finance CSV data analysis."""
    await execution_provider_manager.start()

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    db = _mock_db_with_session()

    with patch("app.agents.execution.artifacts.put_object"):
        result = await DomainAnalysisService.run_finance_analysis_now(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            csv_content=SAMPLE_FINANCE_CSV,
            agent_run_id=run_id,
            provider="mock",
        )

    assert result.status.value in ["completed", "queued"]
    assert result.provider == "mock"
    assert db.add.called
    assert db.commit.called


def test_sales_and_finance_analysis_tools_enqueue_jobs():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _mock_db_with_session()

    sales_res = analyze_sales_data(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        csv_content=SAMPLE_SALES_CSV,
    )
    assert sales_res["status"] == "queued"
    assert "job_id" in sales_res

    fin_res = analyze_financial_data(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        csv_content=SAMPLE_FINANCE_CSV,
    )
    assert fin_res["status"] == "queued"
    assert "job_id" in fin_res


@pytest.mark.asyncio
async def test_chief_of_staff_with_sandbox_csv_analysis():
    """Test ChiefOfStaffOrchestrator delegating CSV analysis to sandbox and ingesting results."""
    await execution_provider_manager.start()

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _mock_db_with_session()

    runtime = MockRuntime()

    with patch("app.agents.execution.artifacts.put_object"):
        with patch("app.agents.orchestration.chief_of_staff.get_pipeline_summary", return_value={"total_pipeline": 100000000}):
            with patch("app.agents.orchestration.chief_of_staff.get_financial_summary", return_value={"runway_months": 8}):
                result = await ChiefOfStaffOrchestrator.orchestrate(
                    db=db,
                    workspace_id=ws_id,
                    user_id=user_id,
                    goal="Tăng trưởng doanh thu Q3 và tối ưu chi phí vận hành",
                    context={
                        "sales_csv": SAMPLE_SALES_CSV,
                        "finance_csv": SAMPLE_FINANCE_CSV,
                    },
                    runtime=runtime,
                )

    assert result.status in ["completed", "partial"]
    assert "sales_sandbox" in result.specialist_reports
    assert "finance_sandbox" in result.specialist_reports
    assert result.specialist_reports["sales_sandbox"]["status"] in ["completed", "queued"]
    assert result.specialist_reports["finance_sandbox"]["status"] in ["completed", "queued"]
