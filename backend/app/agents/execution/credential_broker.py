import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.types import SandboxPolicy
from app.modules.integrations.models import WorkspaceSecret
from app.modules.integrations.secrets_service import decrypt_for_workspace

logger = logging.getLogger(__name__)

# Standard mapping from abstract service names to workspace secret keys and sandbox env variables
SERVICE_SECRET_MAPPING = {
    "openrouter": {
        "secret_key": "openrouter_api_key",
        "env_var": "OPENROUTER_API_KEY",
    },
    "facebook": {
        "secret_key": "facebook_access_token",
        "env_var": "FACEBOOK_ACCESS_TOKEN",
    },
    "github": {
        "secret_key": "github_token",
        "env_var": "GITHUB_TOKEN",
    },
    "google": {
        "secret_key": "google_api_key",
        "env_var": "GOOGLE_API_KEY",
    },
    "slack": {
        "secret_key": "slack_bot_token",
        "env_var": "SLACK_BOT_TOKEN",
    },
}


class CredentialBroker:
    """Brokers encrypted workspace secrets to isolated sandbox containers strictly conforming to policy."""

    @classmethod
    def resolve_credentials(
        cls,
        db: Session,
        workspace_id: int,
        policy: SandboxPolicy,
        requested_services: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Resolve and decrypt allowed workspace credentials into environment variables for sandbox.

        Raises ExecutionRuntimeError if a requested service is not permitted by policy.
        """
        allowed = set(policy.credentials_allow or [])
        env_vars: Dict[str, str] = {}

        services_to_resolve = requested_services if requested_services is not None else list(allowed)

        for service in services_to_resolve:
            service_norm = service.strip().lower()
            if service_norm not in allowed:
                raise ExecutionRuntimeError(
                    code=ExecutionErrorCode.EXEC_CREDENTIAL_NOT_ALLOWED,
                    message=f"Credential for service '{service_norm}' is not allowed by policy '{policy.name}'",
                )

            mapping = SERVICE_SECRET_MAPPING.get(service_norm, {
                "secret_key": f"{service_norm}_secret",
                "env_var": f"{service_norm.upper()}_SECRET",
            })

            secret_key = mapping["secret_key"]
            env_var_name = mapping["env_var"]

            secret_row = (
                db.query(WorkspaceSecret)
                .filter(
                    WorkspaceSecret.workspace_id == workspace_id,
                    WorkspaceSecret.key == secret_key,
                )
                .first()
            )

            if secret_row and secret_row.encrypted_value:
                decrypted = decrypt_for_workspace(workspace_id, secret_row.encrypted_value)
                if decrypted:
                    env_vars[env_var_name] = decrypted
            else:
                logger.info(
                    "[CredentialBroker] Secret key '%s' not configured for workspace %s",
                    secret_key,
                    workspace_id,
                )

        return env_vars

    @classmethod
    def redact_secrets(cls, text: str, secrets: List[str]) -> str:
        """Mask all known secret values from text before sending to LLM context or logs."""
        result = text
        for secret in secrets:
            if secret and len(secret) > 3:
                result = result.replace(secret, "[REDACTED]")
        return result
