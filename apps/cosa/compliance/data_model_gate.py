from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.redaction import Redactor


class CosaDataModelGate:
    def __init__(
        self,
        client: Any = None,
        redactor: Redactor | None = None,
    ) -> None:
        self._client = client
        self._redactor = redactor or Redactor()

    async def prepare_initial_input(self, run_context: Mapping[str, Any], raw_input: str) -> str:
        claim: DataAccessClaim | None = run_context.get("data_access_claim")
        if claim is None and "claim" in run_context:
            raw_c = run_context["claim"]
            if isinstance(raw_c, DataAccessClaim):
                claim = raw_c

        snap = run_context.get("compliance_snapshot") or {}
        dep_id = (
            claim.deployment_id
            if claim
            else (
                snap.get("deployment_id")
                if isinstance(snap, dict)
                else getattr(snap, "deployment_id", None)
            )
        )
        ws_id = claim.workspace_id if claim else run_context.get("workspace_id")
        purpose_id = claim.purpose_id if claim else run_context.get("purpose_id", "advisory")
        provider_key = claim.provider_key if claim else run_context.get("provider_key", "deepseek")
        model_key = claim.model_key if claim else run_context.get("model_key", "")
        capability_id = claim.capability_id if claim else "model.input"
        categories = (
            list(claim.categories)
            if claim
            else list(run_context.get("data_categories") or ["BUSINESS_CONFIDENTIAL"])
        )
        subject_ref = claim.subject_reference if claim else run_context.get("subject_reference")

        # Personal data guard: if personal/sensitive categories requested, subject_reference must be present
        is_personal = any(cat in ("PERSONAL", "SENSITIVE_PERSONAL") for cat in categories)
        if is_personal and not subject_ref:
            raise ComplianceDenied("PROCESSING_AUTHORIZATION_MISSING")

        if self._client and hasattr(self._client, "resolve_data_use"):
            delegation_token = run_context.get("_company_delegation_token") or run_context.get("delegation_token")

            decision = await self._client.resolve_data_use(
                workspace_id=str(ws_id) if ws_id else "",
                deployment_id=str(dep_id) if dep_id else "",
                capability_id=capability_id,
                purpose_id=purpose_id,
                data_categories=categories,
                provider_key=provider_key,
                model_key=model_key,
                subject_reference=subject_ref,
                delegation_token=delegation_token,
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

    async def assert_before_model_call(self, run_context: Mapping[str, Any]) -> None:
        if "compliance_snapshot" in run_context:
            snap = run_context["compliance_snapshot"]
            status = snap.get("status") if isinstance(snap, dict) else getattr(snap, "status", None)
            if status and status != "APPROVED_FOR_USE":
                raise ComplianceDenied("DEPLOYMENT_NOT_APPROVED")
