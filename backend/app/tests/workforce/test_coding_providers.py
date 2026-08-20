import pytest
from app.workforce.adapters.codex import CodexProvider
from app.workforce.adapters.claude import ClaudeCodeProvider

@pytest.mark.asyncio
async def test_codex_provider_contract():
    provider = CodexProvider()
    
    # Giả lập scope không có quyền truy cập credentials production
    scope = {"sandbox_only": True}
    
    result = await provider.start(scope, {}, {"prompt": "test"})
    assert result.status == "started"
    
    cancel_result = await provider.cancel(scope, "codex_run_1")
    assert cancel_result is True
    
    artifacts = await provider.ingest_artifacts(scope, "codex_run_1")
    assert isinstance(artifacts, list)

@pytest.mark.asyncio
async def test_claude_provider_contract():
    provider = ClaudeCodeProvider()
    
    scope = {"sandbox_only": True}
    
    result = await provider.start(scope, {}, {"prompt": "test"})
    assert result.status == "started"
    
    cancel_result = await provider.cancel(scope, "claude_run_1")
    assert cancel_result is True
