from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DeploymentProvider(ABC):
    """Abstract Base Class for programmable infrastructure and Docker Compose VPS deployment."""

    @abstractmethod
    async def deploy_compose_project(
        self,
        vps_id: str,
        project_name: str,
        compose_content: str,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Deploy or initialize a Docker Compose project on target VPS."""
        pass

    @abstractmethod
    async def update_compose_project(
        self,
        vps_id: str,
        project_name: str,
    ) -> Dict[str, Any]:
        """Pull latest images and recreate project containers."""
        pass

    @abstractmethod
    async def restart_project(
        self,
        vps_id: str,
        project_name: str,
    ) -> Dict[str, Any]:
        """Restart project containers."""
        pass

    @abstractmethod
    async def get_project_logs(
        self,
        vps_id: str,
        project_name: str,
        lines: int = 100,
    ) -> Dict[str, Any]:
        """Retrieve recent container logs for project."""
        pass

    @abstractmethod
    async def get_dns_records(
        self,
        domain: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve DNS zone records for target domain."""
        pass

    @abstractmethod
    async def update_dns_records(
        self,
        domain: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update or create DNS records for domain."""
        pass

    @abstractmethod
    async def create_firewall_rule(
        self,
        vps_id: str,
        rule: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Configure firewall port/rule on VPS."""
        pass

    @abstractmethod
    async def create_snapshot(
        self,
        vps_id: str,
        description: str,
    ) -> Dict[str, Any]:
        """Take a VPS disk snapshot before critical modifications."""
        pass

    @abstractmethod
    async def restore_snapshot(
        self,
        vps_id: str,
        snapshot_id: str,
    ) -> Dict[str, Any]:
        """Restore VPS to a previous snapshot."""
        pass
