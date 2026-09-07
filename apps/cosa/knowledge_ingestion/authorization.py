"""Task 6 (plan local-first-enterprise-knowledge) — reusable authorization
resolver cho Vault document/knowledge. Quyết định permission LUÔN tường minh
(structured decision + denial_code) — không suy diễn từ document title, prompt
text hay role client tự khai báo.

Thứ tự resolve (đúng plan Step 3):
1. Workspace operator (founder/co-founder/admin) — full access, không cần grant.
2. Explicit grant (user hoặc role) trên đúng document này.
3. Classification/visibility policy: `visibility=WORKSPACE` cấp read/discover/
   download workspace-wide, TRỪ KHI `classification=RESTRICTED` (RESTRICTED
   luôn cần operator hoặc grant tường minh, kể cả khi visibility=WORKSPACE).
4. `created_by` (chủ sở hữu document) luôn có ít nhất read + manage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from agent.vault.models import VaultClassification, VaultPermission, VaultVisibility
from agent.vault.repository import VaultRepository

__all__ = ["KnowledgeAccessDecision", "KnowledgeAuthorization"]

_WORKSPACE_OPERATOR_ROLES = frozenset({"founder", "co-founder", "admin"})


@dataclass(frozen=True)
class KnowledgeAccessDecision:
    discover: bool
    read: bool
    download: bool
    manage: bool
    review: bool
    publish: bool
    policy_version: int
    denial_code: str | None = None

    @staticmethod
    def deny(*, policy_version: int = 0, denial_code: str) -> KnowledgeAccessDecision:
        return KnowledgeAccessDecision(
            discover=False,
            read=False,
            download=False,
            manage=False,
            review=False,
            publish=False,
            policy_version=policy_version,
            denial_code=denial_code,
        )

    @staticmethod
    def allow_all(*, policy_version: int) -> KnowledgeAccessDecision:
        return KnowledgeAccessDecision(
            discover=True,
            read=True,
            download=True,
            manage=True,
            review=True,
            publish=True,
            policy_version=policy_version,
            denial_code=None,
        )


@runtime_checkable
class _IdentityLike(Protocol):
    """Duck-typed shape (AuthenticatedIdentity thật hoặc test double) — chỉ
    cần principal_id/role_id, tránh import trực tiếp gây phụ thuộc vòng."""

    principal_id: str
    role_id: str


class KnowledgeAuthorization:
    def __init__(self, vault_repository: VaultRepository) -> None:
        self._vault_repository = vault_repository

    async def resolve(
        self, identity: _IdentityLike, document_id: UUID, *, workspace_id: str | None = None
    ) -> KnowledgeAccessDecision:
        ws_id = workspace_id if workspace_id is not None else getattr(identity, "workspace_id", None)
        if ws_id is None:
            raise ValueError("identity phải mang workspace_id, hoặc truyền workspace_id= tường minh")

        document = await self._vault_repository.get_document(ws_id, document_id)
        if document is None:
            return KnowledgeAccessDecision.deny(denial_code="document_not_found")

        role_id = (identity.role_id or "").lower()

        # 1. Workspace operator — full access, không cần grant.
        if role_id in _WORKSPACE_OPERATOR_ROLES:
            return KnowledgeAccessDecision.allow_all(policy_version=document.access_policy_version)

        role_ids = {identity.role_id} if identity.role_id else set()

        # 2. Explicit grant trên đúng document này (kiểm từng permission riêng
        #    lẻ — KHÔNG suy diễn "có 1 quyền là có mọi quyền").
        async def _granted(permission: VaultPermission) -> bool:
            return await self._vault_repository.has_explicit_grant(
                ws_id, document_id, identity.principal_id, role_ids, permission
            )

        is_owner = document.created_by == identity.principal_id
        explicit_read = await _granted(VaultPermission.READ)
        explicit_review = await _granted(VaultPermission.REVIEW)
        explicit_publish = await _granted(VaultPermission.PUBLISH)
        explicit_manage = await _granted(VaultPermission.MANAGE)

        # 3. Classification/visibility policy — WORKSPACE visibility cấp read
        #    workspace-wide, TRỪ document RESTRICTED (luôn cần operator/grant
        #    tường minh kể cả khi visibility=WORKSPACE).
        workspace_wide_read = (
            document.visibility == VaultVisibility.WORKSPACE
            and document.classification != VaultClassification.RESTRICTED
        )

        read = is_owner or explicit_read or workspace_wide_read
        manage = is_owner or explicit_manage
        review = explicit_review
        publish = explicit_publish
        # discover — biết document tồn tại — theo bất kỳ quyền nào ở trên,
        # không riêng read (vd. reviewer thấy document trong hàng đợi review
        # dù chưa có quyền đọc nội dung đầy đủ qua route thường).
        discover = read or manage or review or publish

        if not discover:
            return KnowledgeAccessDecision.deny(
                policy_version=document.access_policy_version, denial_code="not_granted"
            )

        return KnowledgeAccessDecision(
            discover=discover,
            read=read,
            download=read,
            manage=manage,
            review=review,
            publish=publish,
            policy_version=document.access_policy_version,
            denial_code=None,
        )
