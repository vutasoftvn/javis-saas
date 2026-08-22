from __future__ import annotations

_UNPINNED_REFS = {"main", "master", "head", "latest", ""}


class UnpinnedSkillSourceError(Exception):
    def __init__(self, skill_identifier: str) -> None:
        super().__init__(
            f"{skill_identifier!r} has no pinned commit — refusing to proceed "
            "from a moving ref (blueprint §28)"
        )
        self.skill_identifier = skill_identifier


def require_pinned_commit(skill_identifier: str, commit: str | None) -> str:
    """Enforce blueprint §28: never import from a dynamic git ref like
    `main`. Returns the validated commit sha for convenience.
    """
    normalized = (commit or "").strip().lower()
    if not normalized or normalized in _UNPINNED_REFS:
        raise UnpinnedSkillSourceError(skill_identifier)
    return normalized
