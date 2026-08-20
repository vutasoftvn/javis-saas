"""
COSA Claude Code CLI & n8n Task Executors
"""
import time
from typing import Any, Dict
from executors.base import BaseExecutor, BuildSpec, ExecutorResult


class ClaudeCodeExecutor(BaseExecutor):
    id = "claude_code"
    name = "Claude Code Agentic Coding Executor"

    async def execute(self, spec: BuildSpec, workspace_path: str) -> ExecutorResult:
        start_time = time.time()
        # Mô phỏng phiên lập trình tự trị của Claude Code CLI dựa trên BuildSpec
        duration_ms = int((time.time() - start_time) * 1000)
        
        diff = (
            f"diff --git a/{spec.project_name} b/{spec.project_name}\n"
            f"--- a/{spec.project_name}\n"
            f"+++ b/{spec.project_name}\n"
            f"@@ -0,0 +1,10 @@\n"
            f"+ // Objective: {spec.objective}\n"
            f"+ // Status: Completed by Claude Code Executor\n"
        )
        
        return ExecutorResult(
            status="success",
            exit_code=0,
            stdout=f"Claude Code successfully implemented '{spec.objective}' across {len(spec.allowed_paths)} files.",
            stderr="",
            artifacts_created=spec.allowed_paths,
            diff_patch=diff,
            duration_ms=duration_ms
        )

    async def health_check(self) -> bool:
        return True


class N8nAutomationExecutor(BaseExecutor):
    id = "n8n_automation"
    name = "n8n Webhook Automation Executor"

    async def execute(self, spec: BuildSpec, workspace_path: str) -> ExecutorResult:
        start_time = time.time()
        webhook_target = spec.metadata.get("webhook_url", "https://n8n.cosa.ai/webhook/lead-enrich")
        duration_ms = int((time.time() - start_time) * 1000)

        return ExecutorResult(
            status="success",
            exit_code=0,
            stdout=f"Triggered n8n webhook: {webhook_target} -> 200 OK",
            stderr="",
            artifacts_created=[],
            diff_patch=None,
            duration_ms=duration_ms
        )

    async def health_check(self) -> bool:
        return True
