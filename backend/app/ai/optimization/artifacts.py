"""Artifact storage and versioning for compiled DSPy programs.

Enforces Invariant: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS (§P5).
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ProgramArtifactManifest(BaseModel):
    """Manifest describing a compiled and versioned program artifact."""

    program_key: str
    program_version: str
    dspy_version: str = "3.3.0"
    created_at: str
    optimizer: str = "gepa"
    model_policy: str = "fast_reasoning"
    baseline_score: float = 0.0
    candidate_score: float = 0.0
    artifact_hash: str = ""
    status: str = "candidate"  # "candidate", "approved", "rejected"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class ProgramArtifactStore:
    """Manages immutable file artifacts for compiled DSPy programs."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts", "dspy"
        )

    def _get_program_dir(self, program_key: str, version: str) -> str:
        safe_key = program_key.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_dir, safe_key, version)

    def save_artifact(
        self,
        program_key: str,
        version: str,
        program_state: Dict[str, Any],
        manifest: ProgramArtifactManifest,
    ) -> str:
        """Save program state and manifest immutably with SHA256 checksum."""
        target_dir = self._get_program_dir(program_key, version)
        os.makedirs(target_dir, exist_ok=True)

        state_path = os.path.join(target_dir, "program.json")
        manifest_path = os.path.join(target_dir, "manifest.json")
        hash_path = os.path.join(target_dir, "sha256.txt")

        # Serialize state
        state_content = json.dumps(program_state, indent=2, ensure_ascii=False)
        hasher = hashlib.sha256(state_content.encode("utf-8"))
        artifact_hash = hasher.hexdigest()

        # Update manifest hash
        manifest.artifact_hash = artifact_hash

        with open(state_path, "w", encoding="utf-8") as f:
            f.write(state_content)

        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        with open(hash_path, "w", encoding="utf-8") as f:
            f.write(f"{artifact_hash}  program.json\n")

        return target_dir

    def load_artifact(self, program_key: str, version: str) -> Optional[Dict[str, Any]]:
        """Load program state from disk after verifying hash integrity."""
        target_dir = self._get_program_dir(program_key, version)
        state_path = os.path.join(target_dir, "program.json")
        hash_path = os.path.join(target_dir, "sha256.txt")

        if not os.path.exists(state_path):
            return None

        with open(state_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify hash if present
        if os.path.exists(hash_path):
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            with open(hash_path, "r", encoding="utf-8") as f:
                expected_hash = f.read().split()[0]
            if current_hash != expected_hash:
                raise ValueError(
                    f"Integrity check failed for program '{program_key}' v{version}. "
                    f"Expected hash {expected_hash}, got {current_hash}."
                )

        return json.loads(content)

    def load_manifest(self, program_key: str, version: str) -> Optional[ProgramArtifactManifest]:
        """Load artifact manifest from disk."""
        target_dir = self._get_program_dir(program_key, version)
        manifest_path = os.path.join(target_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return None
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProgramArtifactManifest(**data)

    def approve_artifact(
        self,
        program_key: str,
        version: str,
        approved_by: Optional[str],
    ) -> ProgramArtifactManifest:
        """Approve an optimized DSPy artifact for production promotion.
        
        INVARIANT ENFORCEMENT:
        NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
        """
        if not approved_by or approved_by.startswith("agent:") or approved_by.lower() == "system":
            raise PermissionError(
                "Invariant Violation: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS. "
                "DSPy artifact approval requires human admin/founder credentials."
            )

        manifest = self.load_manifest(program_key, version)
        if not manifest:
            raise FileNotFoundError(f"Artifact manifest not found for '{program_key}' v{version}")

        now = datetime.now(timezone.utc).isoformat()
        manifest.status = "approved"
        manifest.approved_by = approved_by
        manifest.approved_at = now

        target_dir = self._get_program_dir(program_key, version)
        manifest_path = os.path.join(target_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        return manifest
