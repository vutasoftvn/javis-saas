"""
Test suite for skillpack contract validation.

Tests cover:
- YAML sequence root (invalid)
- Absent/malformed SKILL.md frontmatter
- Invalid dotted/underscored names
- Duplicate normalized names
- Missing required manifest sections
- Entrypoint validation
- Mismatched source.path
- Non-string runtime tools
- Tool contract violations (declared but unused, or called but undeclared)
"""

import re
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from packages.agent_core.skills.skillpack_contract import (
    SkillpackViolation,
    normalize_discovery_name,
    validate_skillpack_tree,
    _parse_skillmd_frontmatter,
)


def find_repo_root() -> Path:
    """Walk up from this file to find repo root (contains packages/ and skillpacks/)."""
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "packages").exists() and (current / "skillpacks").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repo root (contains packages/ and skillpacks/)")


REPO_ROOT = find_repo_root()


class TestNormalizeDiscoveryName:
    """Test the normalize_discovery_name function."""

    def test_lowercase_conversion(self):
        assert normalize_discovery_name("Tasks") == "tasks"
        assert normalize_discovery_name("OPERATIONS") == "operations"

    def test_dot_to_dash(self):
        assert normalize_discovery_name("operations.tasks") == "operations-tasks"
        assert normalize_discovery_name("strategy.decision-capture") == "strategy-decision-capture"

    def test_underscore_to_dash(self):
        assert normalize_discovery_name("operation_tasks") == "operation-tasks"
        assert normalize_discovery_name("my_skill_name") == "my-skill-name"

    def test_collapse_repeated_dashes(self):
        assert normalize_discovery_name("operations--tasks") == "operations-tasks"
        assert normalize_discovery_name("a---b") == "a-b"

    def test_strip_leading_trailing_dashes(self):
        assert normalize_discovery_name("-tasks-") == "tasks"
        assert normalize_discovery_name("--operations--") == "operations"

    def test_strip_whitespace(self):
        assert normalize_discovery_name("  tasks  ") == "tasks"
        assert normalize_discovery_name(" operations.tasks ") == "operations-tasks"

    def test_complex_examples(self):
        assert normalize_discovery_name("Operations.Tasks") == "operations-tasks"
        assert normalize_discovery_name("strategy.decision_capture") == "strategy-decision-capture"
        assert normalize_discovery_name("--my_skill.name--") == "my-skill-name"


class TestSkillpackContractViolations:
    """Unit tests for individual violation scenarios."""

    def test_manifest_yaml_sequence_root(self):
        """Detect when manifest.yaml has a sequence (array) root instead of mapping."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            # Write a YAML sequence root
            (pack_dir / "manifest.yaml").write_text(
                """- apiVersion: agentos.ai/v1
  kind: Skill
  metadata:
    id: test.pack
"""
            )
            # Minimal valid frontmatter
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "manifest-root-mapping" for v in violations)

    def test_manifest_missing_required_section(self):
        """Detect missing required manifest sections."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            # Missing several required sections
            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
"""
            )
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            missing_rules = [v.rule for v in violations if v.rule.startswith("manifest-missing")]
            # Should catch missing publisher, source, capability, runtime, permissions, risk, trust
            assert len(missing_rules) > 0

    def test_skillmd_absent_frontmatter(self):
        """Detect missing frontmatter in SKILL.md."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            # Minimal valid manifest
            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            # No frontmatter, just content
            (pack_dir / "SKILL.md").write_text("# Just Content\nNo frontmatter here.")

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "frontmatter-missing" for v in violations)

    def test_skillmd_malformed_frontmatter(self):
        """Detect malformed frontmatter (missing closing delimiter)."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            # Opening --- but no closing ---
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
# Missing closing ---
# Content here
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "frontmatter-malformed" for v in violations)

    def test_skillmd_missing_name_field(self):
        """Detect missing name field in frontmatter."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            # Missing name field
            (pack_dir / "SKILL.md").write_text(
                """---
description: Test only
---
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(
                "frontmatter" in v.rule and "name" in v.message.lower() for v in violations
            )

    def test_name_not_normalized(self):
        """Detect when frontmatter name doesn't match normalized metadata.id."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: operations.tasks
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            # Name is "tasks" but should be "operations-tasks" (normalized from operations.tasks)
            (pack_dir / "SKILL.md").write_text(
                """---
name: tasks
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "name-not-normalized" for v in violations)

    def test_duplicate_normalized_names(self):
        """Detect duplicate normalized names across packs."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create two packs with same normalized name
            for i in range(2):
                pack_dir = root / f"pack_{i}"
                pack_dir.mkdir()

                (pack_dir / "manifest.yaml").write_text(
                    f"""apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.sample
publisher:
  name: test
source:
  path: skillpacks/pack_{i}
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
                )
                (pack_dir / "SKILL.md").write_text(
                    """---
name: test-sample
description: Test
---
"""
                )

            violations = validate_skillpack_tree(root)
            # Should catch duplicate on second occurrence
            duplicates = [v for v in violations if v.rule == "name-duplicate"]
            assert len(duplicates) > 0

    def test_entrypoint_invalid(self):
        """Detect when entrypoint is not SKILL.md."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: instructions
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "entrypoint-invalid" for v in violations)

    def test_source_path_mismatch(self):
        """Detect when source.path doesn't match pack directory."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "actual_dir"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/wrong_dir
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "source-path-mismatch" for v in violations)

    def test_runtime_tools_not_string_list(self):
        """Detect when runtime.tools contains non-string elements."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools:
    - tool_name
    - 123
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "runtime-tools-not-string-list" for v in violations)

    def test_tool_declared_but_not_called(self):
        """Detect tools declared in manifest but not called in instructions."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools:
    - unused_tool
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            # SKILL.md doesn't mention the tool anywhere
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---

# Some instructions

No tool calls here.
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "tool-declared-unused" for v in violations)

    def test_tool_called_but_not_declared(self):
        """Detect tool calls in instructions not declared in manifest."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "test_pack"
            pack_dir.mkdir()

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: test.pack
publisher:
  name: test
source:
  path: skillpacks/test_pack
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            # SKILL.md mentions a tool in Allowed Tool Calls
            (pack_dir / "SKILL.md").write_text(
                """---
name: test-pack
description: Test
---

## Allowed Tool Calls

- `undeclared_tool`: Does something

Some other content.
"""
            )

            violations = validate_skillpack_tree(root)
            assert any(v.rule == "tool-not-declared" for v in violations)

    def test_nested_pack_structure(self):
        """Test nested pack discovery (e.g., marketing/campaign-review)."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pack_dir = root / "marketing" / "campaign-review"
            pack_dir.mkdir(parents=True)

            (pack_dir / "manifest.yaml").write_text(
                """apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: marketing.campaign-review
publisher:
  name: test
source:
  path: skillpacks/marketing/campaign-review
capability:
  domain: test
  category: pack
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required: []
risk:
  level: low
trust:
  tier: T0
"""
            )
            (pack_dir / "SKILL.md").write_text(
                """---
name: marketing-campaign-review
description: Test
---
"""
            )

            violations = validate_skillpack_tree(root)
            # Should find this nested pack and validate it
            assert len(violations) == 0 or not any(
                v.path.relative_to(root).parts[0] == "marketing" for v in violations
            )


class TestRepositoryContract:
    """Integration test against the real repository."""

    def test_real_skillpack_repository(self):
        """
        Validate all real skillpacks in the repository.

        Expected: this test will FAIL until Task 2 fixes all packs.
        Do NOT weaken this assertion to make it pass.
        This is the baseline that Task 2 must clear.
        """
        violations = validate_skillpack_tree(REPO_ROOT / "skillpacks")

        # Intentionally strict: should have NO violations when Task 2 is done
        # For now, document what violations exist
        if violations:
            # Print for debugging/documentation
            for v in violations:
                pass  # Just iterate; the assertion below will capture failures

        assert violations == [], (
            f"Found {len(violations)} skillpack violations. "
            "Task 2 must fix all packs to make this test pass."
        )

    def test_repaired_skillpack_contracts(self):
        """
        Validate that all repaired skillpacks meet the contract requirements.

        Per Task 2 Step 1, every pack must satisfy:
        - manifest["runtime"]["entrypoint"] == "SKILL.md"
        - frontmatter["name"] == normalize_discovery_name(manifest["metadata"]["id"])
        - manifest["source"]["path"] == pack.relative_to(REPO_ROOT).as_posix()
        """
        skillpacks_root = REPO_ROOT / "skillpacks"

        # Find all packs (directories with manifest.yaml and SKILL.md)
        packs = []
        for item in skillpacks_root.rglob("*"):
            if item.is_dir():
                manifest_path = item / "manifest.yaml"
                skillmd_path = item / "SKILL.md"
                if manifest_path.exists() and skillmd_path.exists():
                    packs.append(item)

        assert len(packs) == 16, f"Expected 16 packs, found {len(packs)}"

        for pack in sorted(packs):
            manifest_path = pack / "manifest.yaml"
            skillmd_path = pack / "SKILL.md"

            # Load manifest
            manifest = yaml.safe_load(manifest_path.read_text())
            assert isinstance(manifest, dict), f"{pack}: manifest root must be a mapping"

            # Load SKILL.md frontmatter
            skillmd_text = skillmd_path.read_text()
            frontmatter, error = _parse_skillmd_frontmatter(skillmd_text)
            assert error is None, f"{pack}: {error}"
            assert isinstance(frontmatter, dict), f"{pack}: frontmatter must be a mapping"

            # Test 1: entrypoint must be SKILL.md
            assert manifest["runtime"]["entrypoint"] == "SKILL.md", (
                f"{pack}: runtime.entrypoint must be 'SKILL.md', "
                f"got '{manifest['runtime']['entrypoint']}'"
            )

            # Test 2: name must be normalized form of metadata.id
            metadata_id = manifest["metadata"]["id"]
            expected_name = normalize_discovery_name(metadata_id)
            actual_name = frontmatter["name"]
            assert actual_name == expected_name, (
                f"{pack}: frontmatter.name must be '{expected_name}' "
                f"(normalized from '{metadata_id}'), got '{actual_name}'"
            )

            # Test 3: source.path must match pack directory
            expected_path = pack.relative_to(REPO_ROOT).as_posix()
            actual_path = manifest["source"]["path"]
            # Normalize to compare (remove trailing slashes)
            expected_path_normalized = expected_path.rstrip("/")
            actual_path_normalized = actual_path.rstrip("/")
            assert actual_path_normalized == expected_path_normalized, (
                f"{pack}: source.path must be '{expected_path_normalized}', "
                f"got '{actual_path_normalized}'"
            )
