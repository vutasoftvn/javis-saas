from __future__ import annotations

import shutil
from pathlib import Path


class ArtifactAlreadyExistsError(Exception):
    def __init__(self, skill_id: str, commit: str, artifact_dir: Path) -> None:
        super().__init__(
            f"Immutable artifact for {skill_id}@{commit} already exists at {artifact_dir} — "
            "refusing to overwrite (blueprint §27 STORE IMMUTABLE ARTIFACT)"
        )
        self.skill_id = skill_id
        self.commit = commit
        self.artifact_dir = artifact_dir


class ImmutableArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def artifact_dir(self, skill_id: str, commit: str) -> Path:
        return self._root / skill_id / commit

    def store(self, skill_id: str, commit: str, source_dir: Path) -> Path:
        target_dir = self.artifact_dir(skill_id, commit)
        if target_dir.exists():
            raise ArtifactAlreadyExistsError(skill_id, commit, target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)
        return target_dir
