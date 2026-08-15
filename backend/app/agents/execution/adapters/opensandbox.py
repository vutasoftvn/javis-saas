import base64
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from app.agents.execution.base import ExecutionProvider
from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.types import (
    ExecutionHealth,
    ExecutionStepResult,
    SandboxPolicy,
)

logger = logging.getLogger(__name__)


class OpenSandboxExecutor(ExecutionProvider):
    """Execution Provider adapter integrating with upstream OpenSandbox server via Python SDK."""

    def __init__(
        self,
        domain: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.domain = domain or os.environ.get("OPEN_SANDBOX_DOMAIN", "http://opensandbox:8080")
        self.api_key = api_key or os.environ.get("OPEN_SANDBOX_API_KEY", "")
        self._sandboxes: Dict[str, Any] = {}

        # Lazy import opensandbox SDK
        self._sdk_available = False
        try:
            import opensandbox
            self._opensandbox = opensandbox
            self._sdk_available = True
        except ImportError:
            self._opensandbox = None
            logger.warning("[OpenSandboxExecutor] opensandbox Python package not installed")

    @property
    def provider_name(self) -> str:
        return "opensandbox"

    async def create_workspace(
        self,
        policy: SandboxPolicy,
        metadata: Optional[dict] = None,
        env: Optional[dict] = None,
    ) -> str:
        if not self._sdk_available or self._opensandbox is None:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_PROVIDER_UNAVAILABLE,
                message="opensandbox SDK is not installed or available in this environment",
            )

        from opensandbox import Sandbox
        from opensandbox.config.connection import ConnectionConfig

        connection_config = ConnectionConfig(
            domain=self.domain,
            api_key=self.api_key or None,
            use_ssl=self.domain.startswith("https"),
        )

        resource_spec = {
            "cpu": f"{policy.cpu}",
            "memory": f"{policy.memory_mb}Mi",
            "disk": f"{policy.disk_mb}Mi",
        }

        # Safe metadata: only pass non-sensitive tracking information
        safe_meta = {
            "policy_name": policy.name,
            "runtime": "cosa_execution_runtime",
        }
        if metadata:
            for k, v in metadata.items():
                if k in ["job_id", "workspace_id", "agent_key"]:
                    safe_meta[k] = str(v)

        timeout = timedelta(seconds=policy.timeout_seconds)

        try:
            sandbox = await Sandbox.create(
                image=policy.image,
                resource=resource_spec,
                timeout=timeout,
                metadata=safe_meta,
                env=env or {},
                connection_config=connection_config,
            )
            sandbox_id = str(sandbox.id)
            self._sandboxes[sandbox_id] = sandbox
            logger.info(f"[OpenSandboxExecutor] Created sandbox: {sandbox_id} with policy {policy.name}")
            return sandbox_id
        except Exception as exc:
            logger.exception(f"[OpenSandboxExecutor] Failed to create sandbox: {exc}")
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Failed to create OpenSandbox workspace: {exc}",
            )

    async def execute(
        self,
        sandbox_id: str,
        command: str,
        timeout_seconds: int,
    ) -> ExecutionStepResult:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found or active",
            )

        from opensandbox.models.execd import RunCommandOpts

        start_time = datetime.now(timezone.utc)
        opts = RunCommandOpts(timeout=timedelta(seconds=timeout_seconds))

        try:
            exec_result = await sandbox.commands.run(command, opts=opts)
            stdout_text = ""
            stderr_text = ""
            if exec_result.logs:
                if exec_result.logs.stdout:
                    stdout_text = "".join(msg.text for msg in exec_result.logs.stdout)
                if exec_result.logs.stderr:
                    stderr_text = "".join(msg.text for msg in exec_result.logs.stderr)

            exit_code = exec_result.exit_code if exec_result.exit_code is not None else 0
            status = "completed" if exit_code == 0 else "failed"

            return ExecutionStepResult(
                command=command,
                status=status,
                exit_code=exit_code,
                stdout_excerpt=stdout_text,
                stderr_excerpt=stderr_text,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.exception(f"[OpenSandboxExecutor] Command execution error on sandbox {sandbox_id}: {exc}")
            return ExecutionStepResult(
                command=command,
                status="failed",
                exit_code=-1,
                stderr_excerpt=f"Execution error: {exc}",
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )

    async def upload_file(self, sandbox_id: str, path: str, data: bytes) -> None:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )

        from opensandbox.models.filesystem import WriteEntry

        b64_data = base64.b64encode(data).decode("utf-8")
        entry = WriteEntry(
            path=path,
            data=b64_data,
            encoding="base64",
        )

        try:
            await sandbox.files.write_files([entry])
        except Exception as exc:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_FILE_ERROR,
                message=f"Failed to upload file '{path}' to sandbox: {exc}",
            )

    async def download_file(self, sandbox_id: str, path: str) -> bytes:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )

        try:
            content_str = await sandbox.files.read_file(path)
            return content_str.encode("utf-8")
        except Exception as exc:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_FILE_ERROR,
                message=f"Failed to download file '{path}' from sandbox: {exc}",
            )

    async def list_outputs(self, sandbox_id: str, prefix: str = "/output") -> List[str]:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_SANDBOX_CREATE_FAILED,
                message=f"Sandbox '{sandbox_id}' not found",
            )

        from opensandbox.models.filesystem import SearchEntry

        try:
            entry_infos = await sandbox.files.search(SearchEntry(path=prefix))
            return [e.path for e in entry_infos]
        except Exception as exc:
            logger.warning(f"[OpenSandboxExecutor] list_outputs failed on {sandbox_id}: {exc}")
            return []

    async def terminate(self, sandbox_id: str) -> None:
        sandbox = self._sandboxes.pop(sandbox_id, None)
        if sandbox:
            try:
                await sandbox.destroy()
                logger.info(f"[OpenSandboxExecutor] Destroyed sandbox: {sandbox_id}")
            except Exception as exc:
                logger.warning(f"[OpenSandboxExecutor] Error destroying sandbox {sandbox_id}: {exc}")

    async def health(self) -> ExecutionHealth:
        if not self._sdk_available:
            return ExecutionHealth(
                provider="opensandbox",
                available=False,
                version=None,
                active_sandboxes=0,
                details={"error": "SDK not installed"},
            )

        is_healthy = False
        details = {}
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                headers = {}
                if self.api_key:
                    headers["OPEN-SANDBOX-API-KEY"] = self.api_key
                resp = await client.get(f"{self.domain.rstrip('/')}/health", headers=headers)
                if resp.status_code == 200:
                    is_healthy = True
                    details = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                else:
                    details = {"status_code": resp.status_code}
        except Exception as exc:
            details = {"error": str(exc)}

        return ExecutionHealth(
            provider="opensandbox",
            available=is_healthy,
            version=self._opensandbox.__version__ if hasattr(self._opensandbox, "__version__") else "0.1.15",
            active_sandboxes=len(self._sandboxes),
            details=details,
        )
