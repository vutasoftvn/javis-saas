from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.compliance.redaction import Redactor


class CosaDataModelGate:
    def __init__(
        self,
        client: Any = None,
        redactor: Redactor | None = None,
    ) -> None:
        self._client = client
        self._redactor = redactor or Redactor()

    async def prepare_initial_input(
        self, run_context: Mapping[str, Any], raw_input: str
    ) -> str:
        if self._client and hasattr(self._client, "resolve_data_use"):
            ws_id = run_context.get("workspace_id")
            snap = run_context.get("compliance_snapshot") or {}
            dep_id = snap.get("deployment_id") if isinstance(snap, dict) else getattr(snap, "deployment_id", None)
            purpose_id = run_context.get("purpose_id", "advisory")
            provider_key = run_context.get("provider_key", "deepseek")

            decision = await self._client.resolve_data_use(
                workspace_id=ws_id,
                deployment_id=dep_id,
                capability_id="model.input",
                purpose_id=purpose_id,
                data_categories=["PERSONAL", "BUSINESS_CONFIDENTIAL"],
                provider_key=provider_key,
            )
            if hasattr(decision, "allowed") and not decision.allowed:
                raise ComplianceDenied(getattr(decision, "denial_code", "DATA_USE_DENIED"))

            return self._redactor.minimize(raw_input, decision)

        return self._redactor.sanitize(raw_input)

    async def prepare_tool_output(
        self, run_context: Mapping[str, Any], capability_id: str, output: Any
    ) -> Any:
        if isinstance(output, str):
            return self._redactor.sanitize(output)
        if isinstance(output, dict):
            import json
            sanitized_str = self._redactor.sanitize(json.dumps(output))
            return json.loads(sanitized_str)
        return output

    async def assert_before_model_call(
        self, run_context: Mapping[str, Any]
    ) -> None:
        if "compliance_snapshot" in run_context:
            snap = run_context["compliance_snapshot"]
            status = snap.get("status") if isinstance(snap, dict) else getattr(snap, "status", None)
            if status and status != "APPROVED_FOR_USE":
                raise ComplianceDenied("DEPLOYMENT_NOT_APPROVED")
