"""Workspace Vault — cô lập vật lý object-store theo từng workspace (M3).

`WorkspaceObjectStore` là abstraction để business code KHÔNG ghép raw path.
Row-prefix `workspace_id` ≠ physical isolation (guardrail 4): mỗi workspace có
cây thư mục / key-space riêng, mọi thao tác bind `(workspace_id, object_id)`.
"""

from agent_core.vault.object_store import (
    LocalFilesystemWorkspaceStore,
    ObjectRef,
    VaultSecurityError,
    WorkspaceObjectStore,
)

__all__ = [
    "LocalFilesystemWorkspaceStore",
    "ObjectRef",
    "VaultSecurityError",
    "WorkspaceObjectStore",
]
