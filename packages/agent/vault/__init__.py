"""Workspace Vault — cô lập vật lý object-store theo từng workspace (M3).

`WorkspaceObjectStore` là abstraction để business code KHÔNG ghép raw path.
Row-prefix `workspace_id` ≠ physical isolation (guardrail 4): mỗi workspace có
cây thư mục / key-space riêng, mọi thao tác bind `(workspace_id, object_id)`.
"""

from agent.vault.backup import BackupManifest, WorkspaceBackup
from agent.vault.host_catalog import (
    HostCatalog,
    WorkspaceCatalogEntry,
    WorkspaceManifest,
)
from agent.vault.keys import WorkspaceKeyError, WorkspaceKeyManager
from agent.vault.lifecycle import (
    DocumentState,
    LifecycleError,
    SopDefinition,
    SopStatus,
    SopVersion,
    advance_document_state,
    advance_sop_status,
    assert_publishable,
    select_procedural_sops,
)
from agent.vault.object_store import (
    LocalFilesystemWorkspaceStore,
    ObjectRef,
    VaultSecurityError,
    WorkspaceObjectStore,
)
from agent.vault.quota import (
    QuotaDecision,
    QuotaExceededError,
    WorkspaceStorageQuota,
)

__all__ = [
    "BackupManifest",
    "DocumentState",
    "HostCatalog",
    "LifecycleError",
    "LocalFilesystemWorkspaceStore",
    "ObjectRef",
    "QuotaDecision",
    "QuotaExceededError",
    "SopDefinition",
    "SopStatus",
    "SopVersion",
    "VaultSecurityError",
    "WorkspaceBackup",
    "WorkspaceCatalogEntry",
    "WorkspaceKeyError",
    "WorkspaceKeyManager",
    "WorkspaceManifest",
    "WorkspaceObjectStore",
    "WorkspaceStorageQuota",
    "advance_document_state",
    "advance_sop_status",
    "assert_publishable",
    "select_procedural_sops",
]
