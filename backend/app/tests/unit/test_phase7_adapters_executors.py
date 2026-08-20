"""
Unit Tests for Phase 7: Model Gateway, Adapters & Task Executors Engine
Kiểm tra tính toàn vẹn của Multi-LLM Routing, Sandbox Security Constraints, BuildSpec Execution và n8n Webhook.
"""
import pytest
from agent_runtime.models.gateway import ModelGateway, model_gateway
from agent_runtime.models.base import ModelCallPayload, ModelCapabilityPolicy
from executors.registry import executor_registry
from executors.base import BuildSpec


@pytest.mark.asyncio
async def test_model_gateway_routing_by_policy():
    """Kiểm tra ModelGateway tự động định tuyến đúng Provider theo Capability Policy"""
    # 1. Policy REASONING -> DeepSeek
    reasoning_payload = ModelCallPayload(
        messages=[{"role": "user", "content": "Phân tích báo cáo tài chính P&L"}],
        policy=ModelCapabilityPolicy.REASONING
    )
    res_reasoning = await model_gateway.generate(reasoning_payload)
    assert res_reasoning.provider == "deepseek"
    assert "deepseek-reasoner" in res_reasoning.model_name

    # 2. Policy FAST -> Anthropic Haiku
    fast_payload = ModelCallPayload(
        messages=[{"role": "user", "content": "Tóm tắt 3 ý chính"}],
        policy=ModelCapabilityPolicy.FAST
    )
    res_fast = await model_gateway.generate(fast_payload)
    assert res_fast.provider == "anthropic"
    assert "haiku" in res_fast.model_name

    # 3. Policy CODING -> Anthropic Sonnet
    coding_payload = ModelCallPayload(
        messages=[{"role": "user", "content": "Viết mã nguồn Clean Architecture"}],
        policy=ModelCapabilityPolicy.CODING
    )
    res_coding = await model_gateway.generate(coding_payload)
    assert res_coding.provider == "anthropic"
    assert "sonnet" in res_coding.model_name


@pytest.mark.asyncio
async def test_sandboxed_shell_executor_path_restrictions():
    """Kiểm tra SandboxedShellExecutor chặn đứng hành vi can thiệp vào file cấm (.env)"""
    shell_exec = executor_registry.get("sandboxed_shell")
    assert shell_exec is not None

    # 1. Cố gắng ghi vào .env -> Bị hủy (Aborted)
    dangerous_spec = BuildSpec(
        task_id="task_hack_01",
        project_name="COSA",
        objective="Sửa cấu hình",
        allowed_paths=["backend/.env"]
    )
    res_bad = await shell_exec.execute(dangerous_spec, workspace_path="/Volumes/SSD/javis-saas")
    assert res_bad.status == "aborted"
    assert res_bad.exit_code == 1
    assert "Security violation" in res_bad.stderr

    # 2. Ghi vào thư mục an toàn -> Thành công (Success)
    safe_spec = BuildSpec(
        task_id="task_build_02",
        project_name="COSA",
        objective="Tái cấu trúc thư mục src/",
        allowed_paths=["backend/src/service.py"],
        tests_to_run=["pytest tests/unit"]
    )
    res_safe = await shell_exec.execute(safe_spec, workspace_path="/Volumes/SSD/javis-saas")
    assert res_safe.status == "success"
    assert res_safe.exit_code == 0
    assert "PASS" in res_safe.stdout


@pytest.mark.asyncio
async def test_claude_code_executor_build_spec():
    """Kiểm tra ClaudeCodeExecutor nhận BuildSpec và trả về diff_patch chuẩn"""
    claude_exec = executor_registry.get("claude_code")
    assert claude_exec is not None

    spec = BuildSpec(
        task_id="task_coding_01",
        project_name="COSA Backend",
        objective="Implement Clean Architecture",
        allowed_paths=["backend/core/base.py", "backend/agent/runtime.py"]
    )
    res = await claude_exec.execute(spec, workspace_path="/Volumes/SSD/javis-saas")

    assert res.status == "success"
    assert res.diff_patch is not None
    assert len(res.artifacts_created) == 2
    assert "diff --git" in res.diff_patch


@pytest.mark.asyncio
async def test_n8n_automation_executor():
    """Kiểm tra N8nAutomationExecutor kích hoạt webhook thành công"""
    n8n_exec = executor_registry.get("n8n_automation")
    assert n8n_exec is not None

    spec = BuildSpec(
        task_id="task_n8n_01",
        project_name="CRM Auto",
        objective="Gửi lead qua n8n",
        metadata={"webhook_url": "https://n8n.cosa.ai/webhook/lead"}
    )
    res = await n8n_exec.execute(spec, workspace_path="/Volumes/SSD/javis-saas")
    assert res.status == "success"
    assert "200 OK" in res.stdout
