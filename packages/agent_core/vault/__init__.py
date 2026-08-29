"""Workspace Vault — cô lập vật lý object-store theo từng workspace (M3).

`WorkspaceObjectStore` là abstraction để business code KHÔNG ghép raw path.
Row-prefix `workspace_id` ≠ physical isolation (guardrail 4): mỗi workspace có
cây thư mục / key-space riêng, mọi thao tác bind `(workspace_id, object_id)`.
"""

from agent_core.vault.backup import BackupManifest, WorkspaceBackup
from agent_core.vault.host_catalog import (
    HostCatalog,
    WorkspaceCatalogEntry,
    WorkspaceManifest,
)
from agent_core.vault.keys import WorkspaceKeyError, WorkspaceKeyManager
from agent_core.vault.object_store import (
    LocalFilesystemWorkspaceStore,
    ObjectRef,
    VaultSecurityError,
    WorkspaceObjectStore,
)

__all__ = [
    "BackupManifest",
    "HostCatalog",
    "LocalFilesystemWorkspaceStore",
    "ObjectRef",
    "VaultSecurityError",
    "WorkspaceBackup",
    "WorkspaceCatalogEntry",
    "WorkspaceKeyError",
    "WorkspaceKeyManager",
    "WorkspaceManifest",
    "WorkspaceObjectStore",
]
