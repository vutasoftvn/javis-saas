import os
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.modules.integrations.deployment_providers.base import DeploymentProvider
from app.modules.integrations.secrets_service import decrypt_for_workspace

logger = logging.getLogger(__name__)


class HostingerError(Exception):
    pass


class HostingerDeploymentProvider(DeploymentProvider):
    """Hostinger VPS deployment provider communicating directly via REST API."""

    DEFAULT_BASE_URL = "https://api.hostinger.com/v1"

    def __init__(self, api_token: str, base_url: Optional[str] = None):
        if not api_token:
            raise ValueError("Hostinger API token is required")
        self.api_token = api_token
        self.base_url = (base_url or os.environ.get("HOSTINGER_API_URL", self.DEFAULT_BASE_URL)).rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def deploy_compose_project(
        self,
        vps_id: str,
        project_name: str,
        compose_content: str,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/docker/compose"
        payload = {
            "name": project_name,
            "compose_file": compose_content,
            "environment": env_vars or {},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger deploy failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "deployed", "project": project_name}

    async def update_compose_project(
        self,
        vps_id: str,
        project_name: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/docker/compose/{project_name}/update"
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger update failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "updated", "project": project_name}

    async def restart_project(
        self,
        vps_id: str,
        project_name: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/docker/compose/{project_name}/restart"
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger restart failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "restarted", "project": project_name}

    async def get_project_logs(
        self,
        vps_id: str,
        project_name: str,
        lines: int = 100,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/docker/compose/{project_name}/logs?lines={lines}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger logs retrieval failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"logs": ""}

    async def get_dns_records(
        self,
        domain: str,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/dns/zones/{domain}/records"
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger DNS query failed [{res.status_code}]: {res.text}")
            data = res.json()
            return data if isinstance(data, list) else data.get("records", [])

    async def update_dns_records(
        self,
        domain: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/dns/zones/{domain}/records"
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.put(url, json={"records": records}, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger DNS update failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "dns_updated"}

    async def create_firewall_rule(
        self,
        vps_id: str,
        rule: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/firewall/rules"
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=rule, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger firewall update failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "rule_created"}

    async def create_snapshot(
        self,
        vps_id: str,
        description: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/snapshots"
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json={"description": description}, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger snapshot failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "snapshot_created"}

    async def restore_snapshot(
        self,
        vps_id: str,
        snapshot_id: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/vps/{vps_id}/snapshots/{snapshot_id}/restore"
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=self._get_headers())
            if res.status_code >= 400:
                raise HostingerError(f"Hostinger snapshot restore failed [{res.status_code}]: {res.text}")
            return res.json() if res.content else {"status": "restored"}


def build_hostinger_provider(db: Session, workspace_id: int) -> HostingerDeploymentProvider:
    """Factory to construct HostingerDeploymentProvider resolving token from workspace secret or env."""
    api_token = decrypt_for_workspace(db, workspace_id, "hostinger")
    if not api_token:
        api_token = os.environ.get("HOSTINGER_API_TOKEN")
    if not api_token:
        raise HostingerError("Chưa cấu hình API Token cho Hostinger trong Workspace")

    return HostingerDeploymentProvider(api_token=api_token)
