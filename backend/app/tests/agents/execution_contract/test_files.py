import pytest
from app.workforce.agents.execution.adapters.mock import MockExecutor
from app.workforce.agents.execution.types import SandboxPolicy


@pytest.mark.asyncio
async def test_mock_upload_and_download_and_list(mock_executor: MockExecutor, sample_policy: SandboxPolicy):
    sandbox_id = await mock_executor.create_workspace(sample_policy)
    test_data = b"sample,csv,data\n1,2,3\n"
    
    await mock_executor.upload_file(sandbox_id, "/input/data.csv", test_data)
    downloaded = await mock_executor.download_file(sandbox_id, "/input/data.csv")
    assert downloaded == test_data

    # Generate outputs
    await mock_executor.execute(sandbox_id, "python analyze.py", timeout_seconds=10)
    outputs = await mock_executor.list_outputs(sandbox_id, prefix="/output")
    
    assert len(outputs) >= 2
    assert "/output/sales_summary.json" in outputs
    assert "/output/sales_report.md" in outputs
