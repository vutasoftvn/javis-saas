from dataclasses import dataclass

class ScopeResolutionError(ValueError):
    pass

@dataclass(frozen=True)
class ScopeRequest:
    operating_unit_id: int | None = None
    offering_id: int | None = None
    initiative_id: int | None = None
    profile_id: str | None = None
    session_id: str | None = None
    grants: tuple[str, ...] = ()

@dataclass(frozen=True)
class ExecutionScope:
    workspace_id: int
    company_id: int
    principal_user_id: int
    principal_member_id: int
    principal_role: str
    operating_unit_id: int | None
    offering_id: int | None
    initiative_id: int | None
    profile_id: str | None
    session_id: str | None
    grants: tuple[str, ...]

    def snapshot(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "company_id": self.company_id,
            "principal_user_id": self.principal_user_id,
            "principal_member_id": self.principal_member_id,
            "principal_role": self.principal_role,
            "operating_unit_id": self.operating_unit_id,
            "offering_id": self.offering_id,
            "initiative_id": self.initiative_id,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "grants": list(self.grants),
        }
