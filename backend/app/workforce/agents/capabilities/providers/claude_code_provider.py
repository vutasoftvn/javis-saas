"""Claude Code CLI Capability Provider.

Executes local developer tasks (code generation, inspection, test execution) via Claude Code CLI under user permissions.
"""

import asyncio
import shutil
import uuid
from typing import List, Dict, Any

from app.workforce.agents.capabilities.base import (
    CapabilityProvider,
    CapabilityRequest,
    CapabilityResult,
    EvidenceObject,
    ProviderHealthResult,
    ProviderHealthStatus,
)


class ClaudeCodeProvider(CapabilityProvider):
    """Local Developer capability provider using Claude Code CLI."""

    @property
    def provider_id(self) -> str:
        return "claude_code"

    @property
    def priority(self) -> int:
        return 20

    async def health(self) -> ProviderHealthResult:
        claude_bin = shutil.which("claude")
        if claude_bin:
            return ProviderHealthResult(
                provider_id=self.provider_id,
                status=ProviderHealthStatus.AVAILABLE,
                message=f"Claude Code CLI available at {claude_bin}",
            )
        return ProviderHealthResult(
            provider_id=self.provider_id,
            status=ProviderHealthStatus.MISSING,
            message="Claude Code CLI ('claude') not found in PATH",
        )

    async def capabilities(self) -> List[str]:
        return ["generate_code", "inspect_repo", "run_tests", "edit_code"]

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        exec_id = request.execution_id or f"exec_cc_{uuid.uuid4().hex[:10]}"
        prompt = request.payload.get("prompt") or request.payload.get("task", "")

        claude_bin = shutil.which("claude")
        if not claude_bin:
            return CapabilityResult(
                ok=False,
                provider=self.provider_id,
                capability=request.capability,
                execution_id=exec_id,
                error="Claude Code CLI is not installed or available on this system.",
            )

        try:
            # Run non-interactive print mode
            proc = await asyncio.create_subprocess_exec(
                claude_bin,
                "-p",
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)

            if proc.returncode == 0:
                output_text = stdout.decode("utf-8", errors="replace")
                return CapabilityResult(
                    ok=True,
                    provider=self.provider_id,
                    capability=request.capability,
                    execution_id=exec_id,
                    data={"output": output_text, "returncode": 0},
                    evidence=EvidenceObject(
                        action="claude_code.exec",
                        execution_id=exec_id,
                        status="success",
                        provider=self.provider_id,
                        details={"prompt_len": len(prompt), "output_len": len(output_text)},
                    ),
                )
            else:
                err_text = stderr.decode("utf-8", errors="replace")
                return CapabilityResult(
                    ok=False,
                    provider=self.provider_id,
                    capability=request.capability,
                    execution_id=exec_id,
                    error=f"Claude Code exited with code {proc.returncode}: {err_text}",
                )

        except asyncio.TimeoutError:
            return CapabilityResult(
                ok=False,
                provider=self.provider_id,
                capability=request.capability,
                execution_id=exec_id,
                error="Execution timed out after 120 seconds.",
            )
        except Exception as exc:
            return CapabilityResult(
                ok=False,
                provider=self.provider_id,
                capability=request.capability,
                execution_id=exec_id,
                error=str(exc),
            )
