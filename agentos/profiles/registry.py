# agentos/profiles/registry.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
import yaml

from agentos.profiles.schema import AgentProfile
from agentos.skills.registry import SkillRegistry
from agentos.tools.registry import ToolRegistry


class ProfileNotFoundError(Exception):
    def __init__(self, profile_id: str) -> None:
        super().__init__(f"Agent profile not found: {profile_id}")
        self.profile_id = profile_id


class ProfileValidationError(Exception):
    def __init__(self, profile_path: Path, reason: str) -> None:
        super().__init__(f"Invalid agent profile at {profile_path}: {reason}")
        self.profile_path = profile_path
        self.reason = reason


class ProfileRegistry:
    """Registry and loader for Agent Profiles (§12.2-12.3).
    Discovers YAML profiles, validates them against schema, and performs
    cross-validation against SkillRegistry and ToolRegistry (fails loudly if
    any referenced skill or tool is not registered).
    """

    def __init__(self) -> None:
        self._profiles: dict[str, AgentProfile] = {}
        self._default_profile_id: str = "co-founder"

    def discover(
        self,
        root: Path,
        *,
        skill_registry: SkillRegistry,
        tool_registry: ToolRegistry,
    ) -> list[str]:
        """Scan root for *.yaml files, validate cross-references, and register profiles."""
        discovered: list[str] = []
        registered_tool_names = set(tool_registry.names())

        for yaml_path in sorted(root.glob("**/*.yaml")):
            try:
                raw_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                profile = AgentProfile(**raw_data)
            except Exception as exc:
                raise ProfileValidationError(yaml_path, str(exc)) from exc

            # Cross-validate skills
            for skill_id in profile.skills:
                if not skill_registry.has(skill_id):
                    raise ProfileValidationError(
                        yaml_path,
                        f"Skill '{skill_id}' referenced in profile '{profile.id}' does not exist in SkillRegistry",
                    )

            # Cross-validate tools
            for tool_name in profile.tools_allow:
                if tool_name not in registered_tool_names:
                    raise ProfileValidationError(
                        yaml_path,
                        f"Tool '{tool_name}' referenced in profile '{profile.id}' does not exist in ToolRegistry",
                    )

            self.register(profile)
            discovered.append(profile.id)

        return discovered

    def register(self, profile: AgentProfile) -> None:
        self._profiles[profile.id] = profile

    def get(self, profile_id: str) -> AgentProfile:
        # Support both 'co-founder' and 'co_founder' lookup
        normalized_id = profile_id.replace("_", "-")
        if profile_id in self._profiles:
            return self._profiles[profile_id]
        if normalized_id in self._profiles:
            return self._profiles[normalized_id]
        raise ProfileNotFoundError(profile_id)

    def get_default(self) -> AgentProfile:
        if self._default_profile_id in self._profiles:
            return self._profiles[self._default_profile_id]
        if self._profiles:
            return next(iter(self._profiles.values()))
        raise ProfileNotFoundError("No default agent profile registered")

    def list(self) -> list[AgentProfile]:
        return list(self._profiles.values())

    def has(self, profile_id: str) -> bool:
        normalized_id = profile_id.replace("_", "-")
        return profile_id in self._profiles or normalized_id in self._profiles
