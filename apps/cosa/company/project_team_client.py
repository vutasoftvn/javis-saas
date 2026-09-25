from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from apps.cosa.auth.jwt import mint_worker_service_jwt

__all__ = [
    "ProjectAgentRunAuthority",
    "ProjectTeamAuthorityError",
    "ProjectTeamClient",
    "SpecRef",
]


class ProjectTeamAuthorityError(Exception):
    """Lỗi khi xác thực quyền chạy của agent với Company plane."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SpecRef(BaseModel):
    id: str
    version: str
    hash: str


class ProjectAgentRunAuthority(BaseModel):
    project_id: str = Field(alias="projectId")
    workspace_id: str = Field(alias="workspaceId")
    profile_key: str = Field(alias="profileKey")
    assignment_version: int = Field(alias="assignmentVersion")
    agent_workforce_member_id: str = Field(alias="agentWorkforceMemberId")
    spec: SpecRef
    policy_snapshot: dict[str, Any] = Field(default_factory=dict, alias="policySnapshot")

    model_config = {"populate_by_name": True}


class ProjectTeamClient:
    """Client gọi Company service internal endpoint để lấy Project Agent run authority.

    Agent Platform KHÔNG trực tiếp kết nối DB Company; toàn bộ authority được
    truy vấn và xác thực qua route internal này có kèm service token.
    """

    @property
    def service_token(self) -> str:
        return self._static_service_token or mint_worker_service_jwt(
            worker_id="project-team-worker"
        )

    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("COMPANY_SERVICE_URL")
            or os.getenv("COMPANY_URL")
            or "http://localhost:4000"
        ).rstrip("/")
        # Không ký JWT ở constructor: token chỉ sống 5 phút nên client sống lâu
        # (tạo lúc worker khởi động) sẽ giữ token hết hạn; ký lại mỗi request.
        self._static_service_token = service_token
        self.timeout = timeout

    async def get_run_authority(
        self,
        *,
        workspace_id: str,
        project_id: str,
        profile_key: str,
    ) -> ProjectAgentRunAuthority:
        """GET /internal/operations/projects/:projectId/startup-team/:profileKey/run-authority"""
        url = f"{self.base_url}/internal/operations/projects/{project_id}/startup-team/{profile_key}/run-authority"
        headers = {
            "X-Workspace-Id": workspace_id,
            "X-Service-Token": self.service_token,
            "Authorization": f"Bearer {self.service_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise ProjectTeamAuthorityError(f"Company service unreachable: {exc}") from exc

        if res.status_code != 200:
            raise ProjectTeamAuthorityError(
                f"Company service denied authority for {profile_key} (status {res.status_code}): {res.text}",
                status_code=res.status_code,
            )

        try:
            data = res.json()
            return ProjectAgentRunAuthority.model_validate(data)
        except Exception as exc:
            raise ProjectTeamAuthorityError(f"Malformed authority response: {exc}") from exc
