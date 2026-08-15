import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.agents.execution.base import ExecutionProvider
from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.types import (
    ExecutionHealth,
    ExecutionStepResult,
    SandboxPolicy,
)


class MockExecutor(ExecutionProvider):
    """In-memory Mock Execution Provider for hermetic testing and local CI."""

    def __init__(self) -> None:
        # sandbox_id -> { "files": { path: bytes }, "policy": SandboxPolicy, "created_at": datetime }
        self._sandboxes: Dict[str, dict] = {}
        self._available: bool = True

    @property
    def provider_name(self) -> str:
        return "mock"

    def set_available(self, available: bool) -> None:
        self._available = available

    async def create_workspace(
        self,
        policy: SandboxPolicy,
        metadata: Optional[dict] = None,
        env: Optional[dict] = None,
    ) -> str:
        if not self._available:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_PROVIDER_UNAVAILABLE,
                message="Mock executor is currently marked unavailable",
            )
        sandbox_id = f"mock-sbx-{uuid.uuid4().hex[:12]}"
        self._sandboxes[sandbox_id] = {
            "files": {},
            "policy": policy,
            "created_at": datetime.now(timezone.utc),
            "metadata": metadata or {},
            "env": env or {},
        }
        return sandbox_id

    async def execute(
        self,
        sandbox_id: str,
        command: str,
        timeout_seconds: int,
    ) -> ExecutionStepResult:
        if not self._available:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_PROVIDER_UNAVAILABLE,
                message="Mock executor is unavailable",
            )
        if sandbox_id not in self._sandboxes:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )

        start_time = datetime.now(timezone.utc)

        # Simulate timeout if command contains "sleep_forever"
        if "sleep_forever" in command or (timeout_seconds > 0 and timeout_seconds < 1 and "sleep" in command):
            await asyncio.sleep(0.01)
            return ExecutionStepResult(
                command=command,
                status="timeout",
                exit_code=-1,
                stderr_excerpt="Execution timed out",
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )

        # Simulate simulated execution logic
        stdout = f"[mock-exec] Executed: {command}\n"
        stderr = ""
        exit_code = 0

        # Special commands simulation
        if "exit 1" in command or "fail" in command:
            exit_code = 1
            stderr = "Mock command error exit code 1"
        elif "analyze.py" in command or "generate_output" in command:
            # Generate simulated output files into /output
            sbx = self._sandboxes[sandbox_id]
            sbx["files"]["/output/sales_summary.json"] = b'{"total_revenue": 150000000, "status": "success"}'
            sbx["files"]["/output/sales_report.md"] = b"# Sales Report\nTotal revenue generated: 150M VND"
            stdout += "Analysis finished. Generated /output/sales_summary.json and /output/sales_report.md\n"

        return ExecutionStepResult(
            command=command,
            status="completed" if exit_code == 0 else "failed",
            exit_code=exit_code,
            stdout_excerpt=stdout,
            stderr_excerpt=stderr,
            started_at=start_time,
            completed_at=datetime.now(timezone.utc),
        )

    async def upload_file(self, sandbox_id: str, path: str, data: bytes) -> None:
        if sandbox_id not in self._sandboxes:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )
        clean_path = os.path.normpath(path)
        self._sandboxes[sandbox_id]["files"][clean_path] = data

    async def download_file(self, sandbox_id: str, path: str) -> bytes:
        if sandbox_id not in self._sandboxes:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )
        clean_path = os.path.normpath(path)
        files = self._sandboxes[sandbox_id]["files"]
        if clean_path in files:
            return files[clean_path]
        raise ExecutionRuntimeError(
            code=ExecutionErrorCode.EXEC_FILE_ERROR,
            message=f"File '{clean_path}' not found in mock sandbox",
        )

    async def list_outputs(self, sandbox_id: str, prefix: str = "/output") -> List[str]:
        if sandbox_id not in self._sandboxes:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )
        clean_prefix = os.path.normpath(prefix)
        files = self._sandboxes[sandbox_id]["files"]
        return [p for p in files.keys() if p.startswith(clean_prefix)]

    async def terminate(self, sandbox_id: str) -> None:
        self._sandboxes.pop(sandbox_id, None)

    async def health(self) -> ExecutionHealth:
        return ExecutionHealth(
            provider="mock",
            available=self._available,
            version="1.0.0-mock",
            active_sandboxes=len(self._sandboxes),
            details={"type": "in_memory"},
        )
