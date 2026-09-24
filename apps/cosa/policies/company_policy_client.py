from __future__ import annotations

import os
from typing import Any

import httpx

from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.policies.snapshot import (
    AgentCapabilityAuthority,
    BusinessPermissionRule,
    BusinessPolicyRuleSet,
    PolicySnapshot,
    TenantPolicyRule,
)

__all__ = ["CosaTenantPolicyClient", "CosaTenantPolicyError"]


class CosaTenantPolicyError(Exception):
    """Không resolve được PolicySnapshot thật — call site PHẢI coi đây là
    DENY/NOT_READY, không phải ALLOW ngầm (§10.5 freshness invariant của
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md)."""


class CosaTenantPolicyClient:
    """Client mỏng gọi `GET /platform/auth/me/agent-policy-snapshot`
    (services/cosa, expose:true, tự verify thủ công — xem
    services/cosa/handlers/agent-policy.handler.ts::getMyTenantPolicySnapshot)
    để lấy toàn bộ `cosa.company_agent_policy` rows của company đang xác thực
    + trạng thái company/user hiện tại, resolve 1 lần tại boundary (run-start
    hoặc trước resume), không gọi lại mỗi tool call.

    `bearer_token` PHẢI là control-plane delegation mint bởi
    `AuthenticatedIdentity.mint_control_plane_delegation()` (B5 fix,
    2026-09-04) — không còn forward/re-sign token gốc của người dùng
    (`mint_delegation()`), vì endpoint phía services/cosa cần verify được
    trực tiếp KHÔNG round-trip sang services/company (khác secret, luôn fail
    — xem apps/cosa/auth/jwt.py::mint_control_plane_delegation).
    """

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 5.0,
        company_base_url: str | None = None,
        company_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or resolve_platform_control_plane_url()).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url, transport=transport, timeout=timeout
        )

        # IA02: evaluate_business_action gọi services/company (Company Business
        # plane) — KHÁC HẲN self._client ở trên vốn trỏ platform control plane
        # (services/cosa) cho get_snapshot. Trước đây evaluate_business_action
        # tái dùng self._client nên request /identity/business-policy/evaluate
        # đi nhầm sang services/cosa (route không tồn tại ở đó). Resolve URL
        # theo cùng biến môi trường COMPANY_SERVICE_URL đã dùng ở
        # apps/cosa/compliance/company_client.py::AiComplianceClient.
        self._company_base_url = (
            company_base_url or os.environ.get("COMPANY_SERVICE_URL") or "http://127.0.0.1:4000"
        ).rstrip("/")
        self._company_client = httpx.AsyncClient(
            base_url=self._company_base_url, transport=company_transport, timeout=timeout
        )

    async def get_snapshot(self, bearer_token: str, workspace_id: str) -> PolicySnapshot:
        try:
            resp = await self._client.get(
                "/platform/auth/me/agent-policy-snapshot",
                params={"organizationId": workspace_id},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise CosaTenantPolicyError(f"không gọi được COSA control plane: {exc}") from exc

        if resp.status_code != 200:
            raise CosaTenantPolicyError(
                f"COSA control plane trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise CosaTenantPolicyError(
                f"COSA control plane trả response không phải JSON: {exc}"
            ) from exc

        try:
            return PolicySnapshot(
                workspace_id=data["organizationId"],
                workspace_status=data["workspaceStatus"],
                principal_status=data["principalStatus"],
                rules=[
                    TenantPolicyRule(
                        tool_pattern=r["toolPattern"],
                        decision=r["decision"],
                        reason=r.get("reason"),
                    )
                    for r in data["rules"]
                ],
                snapshot_hash=data["snapshotHash"],
                business_policy_ref=data.get("businessPolicyRef"),
            )
        except KeyError as exc:
            raise CosaTenantPolicyError(f"response thiếu field bắt buộc: {exc}") from exc

    async def evaluate_business_action(
        self,
        delegation_token: str,
        workspace_id: str,
        action: str,
        resource_ref: str | None = None,
        version: int | None = None,
        run_ref: str | None = None,
        project_id: str | None = None,
        legal_entity_id: str | None = None,
    ) -> dict[str, Any]:
        """Gọi `POST /identity/business-policy/evaluate` trên services/company
        (Company Business plane) — KHÔNG phải services/cosa. `delegation_token`
        PHẢI là JWT mint bởi `apps.cosa.auth.jwt.mint_company_delegation()`
        (ký bằng COSA_COMPANY_DELEGATION_SECRET, scoped
        {workspace_id, run_id, capability_ids}) — không phải bearer token
        platform gốc của user (khác secret, services/company sẽ không verify
        được — cùng lớp lỗi đã gây ra bug B5 cross-plane delegation).
        """
        payload = {
            "action": action,
            "resourceRef": resource_ref,
            "version": version,
            "runRef": run_ref,
            "projectId": project_id,
            "legalEntityId": legal_entity_id,
        }
        try:
            resp = await self._company_client.post(
                "/identity/business-policy/evaluate",
                json=payload,
                headers={
                    "Authorization": f"Bearer {delegation_token}",
                    "X-Workspace-Id": workspace_id,
                },
            )
        except httpx.HTTPError as exc:
            raise CosaTenantPolicyError(f"không gọi được Company service: {exc}") from exc

        if resp.status_code != 200:
            raise CosaTenantPolicyError(
                f"Company business policy evaluate trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json()

    async def get_business_policy_rules(
        self,
        delegation_token: str,
        workspace_id: str,
        workforce_member_id: str | None = None,
        project_id: str | None = None,
        legal_entity_id: str | None = None,
    ) -> BusinessPolicyRuleSet:
        """IA02 phần 2 — gọi `GET /identity/business-policy/rules` trên
        services/company để lấy RAW rule set (chưa evaluate) của 1 workforce
        member, resolve tại boundary run-start/trước resume (CÙNG lúc với
        get_snapshot) rồi nhúng vào PolicySnapshot — CapabilityGateway.evaluate()
        chạy ĐỒNG BỘ nên không thể gọi HTTP tại thời điểm thực thi từng
        capability. `delegation_token` PHẢI mint bởi
        `apps.cosa.auth.jwt.mint_company_delegation()` với capability_ids chứa
        `CAP_BUSINESS_POLICY_RULES_READ` (xem cosa-task-delegation.ts phía
        services/company) — route phía company verify bằng
        verifyCosaDelegationForCapability, không có session fallback.
        """
        params: dict[str, str] = {}
        if workforce_member_id:
            params["workforceMemberId"] = workforce_member_id
        if project_id:
            params["projectId"] = project_id
        if legal_entity_id:
            params["legalEntityId"] = legal_entity_id

        try:
            resp = await self._company_client.get(
                "/identity/business-policy/rules",
                params=params,
                headers={
                    "Authorization": f"Bearer {delegation_token}",
                    "X-Workspace-Id": workspace_id,
                },
            )
        except httpx.HTTPError as exc:
            raise CosaTenantPolicyError(f"không gọi được Company service: {exc}") from exc

        if resp.status_code != 200:
            raise CosaTenantPolicyError(
                f"Company business policy rules trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
            if "policyVersion" not in data or "ruleGroups" not in data:
                raise KeyError("missing required fields policyVersion or ruleGroups")
            return BusinessPolicyRuleSet(
                is_founder=data.get("isFounder", False),
                policy_version=data["policyVersion"],
                authorization_epoch=data.get("authorizationEpoch", 1),
                rule_groups=[
                    [
                        BusinessPermissionRule(
                            permission_key=r["permissionKey"],
                            effect=r["effect"],
                            conditions=r.get("conditions") or {},
                        )
                        for r in group.get("rules", [])
                    ]
                    for group in data["ruleGroups"]
                ],
                agent_capabilities=[
                    AgentCapabilityAuthority(
                        capability_id=c["capabilityId"],
                        permission_key=c["permissionKey"],
                        risk_class=c["riskClass"],
                        grant_id=c["grantId"],
                        constraints=c.get("constraints") or {},
                    )
                    for c in data.get("agentCapabilities", [])
                ],
            )
        except (KeyError, ValueError) as exc:
            raise CosaTenantPolicyError(
                f"Company business policy rules response thiếu field bắt buộc: {exc}"
            ) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
        await self._company_client.aclose()
