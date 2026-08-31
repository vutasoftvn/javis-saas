"""
Static skillpack contract validator.

Validates skillpack source material (manifest.yaml + SKILL.md pairs) without
runtime loading. Reports structure violations, missing sections, and tool
contract mismatches.

Tool-contract extraction heuristic:
- Parses SKILL.md for a markdown heading containing "Allowed Tool Calls"
  (case-insensitive match).
- Extracts capability IDs from backtick-quoted identifiers in the section
  following that heading, until the next heading or end of document.
- Supports both inline backticks (`tool_id`) and list items (- `tool_id`).
- Any tool_id listed there must be declared in manifest.runtime.tools.
- Conversely, any ID in runtime.tools must appear in the instruction body
  OR be explicitly marked optional (regex: r"\(optional\)|nếu có" near mention).

Name normalization:
- Converts to lowercase, replaces dots/underscores with dashes, collapses
  repeated dashes, strips leading/trailing dashes.
- Result must match frontmatter.name exactly (case-sensitive after normalization).
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SkillpackViolation:
    """A single contract violation."""

    path: Path
    rule: str
    message: str


VALID_LIFECYCLE_STAGES = frozenset(
    {
        "P0_DISCOVERY",
        "P1_PROBLEM_VALIDATION",
        "P2_SOLUTION_VALIDATION",
        "P3_BUILD_VALIDATE",
        "P4_GO_TO_MARKET",
        "P5_OPERATE_GROWTH",
        "P6_SCALE_GOVERN",
    }
)
VALID_AUTONOMY_CEILINGS = frozenset({"L0_OBSERVE", "L1_PROPOSE", "L2_BOUNDED"})
VALID_SIDE_EFFECT_CLASSES = frozenset({"R", "A", "B", "X", "M", "D"})


def normalize_discovery_name(value: str) -> str:
    """
    Normalize a discovery name (e.g., 'operations.tasks' → 'operations-tasks').

    Process:
    1. Strip whitespace
    2. Convert to lowercase
    3. Replace . and _ with -
    4. Collapse multiple consecutive -
    5. Strip leading/trailing -
    """
    value = value.strip().lower()
    value = re.sub(r"[._]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def _parse_skillmd_frontmatter(content: str) -> tuple[dict | None, str | None]:
    """
    Parse YAML frontmatter from SKILL.md.

    Expects format:
    ---
    name: ...
    description: ...
    ---
    # Rest of file

    Returns: (parsed_dict, error_message)
    If valid: (dict, None)
    If missing delimiters: (None, error_string)
    If malformed YAML: (None, error_string)
    """
    if not content.startswith("---"):
        return None, "frontmatter-missing"

    rest = content[3:]  # Skip first ---
    end_delim = rest.find("\n---\n")

    if end_delim == -1:
        # Try just --- at end of line (in case of Windows line endings or edge case)
        lines = rest.split("\n")
        delim_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == "---":
                delim_idx = i
                break

        if delim_idx == -1:
            return None, "frontmatter-malformed"

        frontmatter_text = "\n".join(lines[:delim_idx])
    else:
        frontmatter_text = rest[:end_delim]

    try:
        data = yaml.safe_load(frontmatter_text)
        if not isinstance(data, dict):
            return None, "frontmatter-malformed"
        return data, None
    except yaml.YAMLError:
        return None, "frontmatter-malformed"


def _extract_allowed_tools(skillmd_body: str) -> set[str]:
    """
    Extract tool IDs from the 'Allowed Tool Calls' section.

    Looks for a heading containing 'Allowed Tool Calls' (case-insensitive),
    then extracts backtick-quoted identifiers in the section until the next
    heading or end of document.

    Returns a set of tool IDs (e.g., {'strategy.decision_record.create'}).
    """
    # Find the heading (case-insensitive)
    heading_pattern = r"^#+\s+.*allowed\s+tool\s+calls.*$"
    lines = skillmd_body.split("\n")

    allowed_tools = set()
    in_section = False

    for _i, line in enumerate(lines):
        if re.search(heading_pattern, line, re.IGNORECASE):
            in_section = True
            continue

        if in_section:
            # Stop at next heading
            if line.startswith("#") and not line.startswith("####"):
                break

            # Extract backtick-quoted identifiers
            # Patterns: `tool_id`, or list items like - `tool_id`
            backtick_matches = re.findall(r"`([a-zA-Z0-9._-]+)`", line)
            for match in backtick_matches:
                allowed_tools.add(match)

    return allowed_tools


def _extract_referenced_capabilities(skillmd_body: str) -> set[str]:
    """Extract capabilities named under a non-callable reference-only section."""
    heading_pattern = r"^#+\s+.*referenced\s+capabilities\s*\(not\s+callable\).*?$"
    references: set[str] = set()
    in_section = False

    for line in skillmd_body.split("\n"):
        if re.search(heading_pattern, line, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if line.startswith("#") and not line.startswith("####"):
                break
            references.update(re.findall(r"`([a-zA-Z0-9._-]+)`", line))

    return references


def _is_tool_marked_optional(skillmd_body: str, tool_id: str) -> bool:
    """
    Check if a tool is marked as optional in the instruction body.

    Looks for patterns like "(optional)" or "nếu có" near the tool mention.
    """
    lines = skillmd_body.split("\n")
    escaped_tool = re.escape(tool_id)
    pattern = rf"`{escaped_tool}`|{escaped_tool}"

    for line in lines:
        # Check same line for optional markers
        if re.search(pattern, line) and re.search(r"\(optional\)|nếu có", line, re.IGNORECASE):
            return True
    return False


def _find_attribution_ledger(root: Path) -> Path | None:
    """Find skill-source-attribution.md by walking up from root or checking standard paths."""
    current = root.resolve()
    while current != current.parent:
        candidate = current / "docs" / "integrations" / "skill-source-attribution.md"
        if candidate.exists():
            return candidate
        if (current / "packages").exists() and (current / "skillpacks").exists():
            candidate = current / "docs" / "integrations" / "skill-source-attribution.md"
            if candidate.exists():
                return candidate
        current = current.parent
    return None


def _parse_attribution_ledger(ledger_path: Path) -> dict[str, dict[str, str]]:
    """
    Parse skill-source-attribution.md table.
    Returns mapping: skill_id -> dict of column values
    """
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    entries: dict[str, dict[str, str]] = {}
    for raw_line in text.splitlines():
        clean_line = raw_line.strip()
        if not clean_line.startswith("|") or not clean_line.endswith("|"):
            continue
        parts = [p.strip() for p in clean_line.split("|")[1:-1]]
        if len(parts) >= 8:
            skill_id = parts[0].strip("` \t")
            if skill_id in ("cosa_skill_id", "---") or not skill_id or skill_id.startswith("-"):
                continue
            entries[skill_id] = {
                "nhom": parts[1].strip("` "),
                "upstream_repo": parts[2].strip("` "),
                "commit_sha": parts[3].strip("` "),
                "upstream_skills": parts[4].strip("` "),
                "upstream_version": parts[5].strip("` "),
                "license": parts[6].strip("` "),
                "status": parts[7].strip("` "),
            }
    return entries


def _extract_source_attribution_record(skillmd_text: str) -> dict | None:
    """
    Extract and parse YAML block under '## Nguồn' or containing 'upstream:'.
    """
    heading_pattern = r"^#+\s+.*nguồn.*$"
    lines = skillmd_text.split("\n")
    in_source_section = False
    in_code_block = False
    code_lines = []

    for line in lines:
        if re.search(heading_pattern, line, re.IGNORECASE):
            in_source_section = True
            continue

        if in_source_section:
            if line.startswith("```"):
                if in_code_block:
                    break
                else:
                    in_code_block = True
                    continue
            if in_code_block:
                code_lines.append(line)

    if code_lines:
        try:
            parsed = yaml.safe_load("\n".join(code_lines))
            if isinstance(parsed, dict) and "upstream" in parsed:
                return parsed
        except yaml.YAMLError:
            pass

    # Fallback search for ```yaml\nupstream: in the whole file
    match = re.search(r"```(?:yaml)?\s*\n(upstream:.*?\n)```", skillmd_text, re.DOTALL)
    if match:
        try:
            parsed = yaml.safe_load(match.group(1))
            if isinstance(parsed, dict) and "upstream" in parsed:
                return parsed
        except yaml.YAMLError:
            pass

    return None


def validate_skillpack_tree(
    root: Path,
    registered_capabilities: set[str] | None = None,
) -> list[SkillpackViolation]:
    """
    Validate all skillpacks under root directory.

    A pack is any directory (recursively discovered) containing both
    manifest.yaml and SKILL.md directly.

    Returns list of violations sorted by path, then rule.
    """
    violations: list[SkillpackViolation] = []
    seen_normalized_names: dict[str, Path] = {}

    # Recursively find all directories containing both manifest.yaml and SKILL.md
    def find_pack_dirs(search_root: Path) -> list[Path]:
        packs = []
        for item in search_root.rglob("*"):
            if item.is_dir():
                manifest = item / "manifest.yaml"
                skillmd = item / "SKILL.md"
                if manifest.exists() and skillmd.exists():
                    packs.append(item)
        return sorted(packs)

    pack_dirs = find_pack_dirs(root)

    for pack_dir in pack_dirs:
        pack_violations = _validate_single_pack(
            pack_dir, root, registered_capabilities=registered_capabilities
        )
        violations.extend(pack_violations)

        # Track normalized names for duplicate detection
        for v in pack_violations:
            if v.rule == "name-not-normalized":
                continue  # Skip if name is invalid

        # If this pack has a valid name, check for duplicates
        manifest_path = pack_dir / "manifest.yaml"
        skillmd_path = pack_dir / "SKILL.md"

        try:
            manifest = yaml.safe_load(manifest_path.read_text())
            if isinstance(manifest, dict):
                metadata = manifest.get("metadata", {})
                if isinstance(metadata, dict):
                    metadata_id = metadata.get("id", "")
                    if metadata_id:
                        normalized = normalize_discovery_name(metadata_id)

                        skillmd_text = skillmd_path.read_text()
                        frontmatter, _ = _parse_skillmd_frontmatter(skillmd_text)
                        if frontmatter and isinstance(frontmatter, dict):
                            fm_name = frontmatter.get("name", "")
                            if fm_name and fm_name == normalized:
                                # Valid name found; check for duplicate
                                if normalized in seen_normalized_names:
                                    violations.append(
                                        SkillpackViolation(
                                            path=skillmd_path.relative_to(root),
                                            rule="name-duplicate",
                                            message=(
                                                f"Duplicate normalized name '{normalized}' "
                                                f"(also at {seen_normalized_names[normalized]})"
                                            ),
                                        )
                                    )
                                else:
                                    seen_normalized_names[normalized] = skillmd_path.relative_to(
                                        root
                                    )
        except (OSError, yaml.YAMLError):
            pass  # Already reported in _validate_single_pack

    return sorted(violations, key=lambda v: (str(v.path), v.rule))


def _validate_single_pack(
    pack_dir: Path,
    root: Path,
    registered_capabilities: set[str] | None = None,
) -> list[SkillpackViolation]:
    """Validate a single skillpack directory."""
    violations: list[SkillpackViolation] = []
    rel_path = pack_dir.relative_to(root)

    manifest_path = pack_dir / "manifest.yaml"
    skillmd_path = pack_dir / "SKILL.md"

    # Load and validate manifest.yaml
    try:
        manifest_text = manifest_path.read_text()
        manifest = yaml.safe_load(manifest_text)
    except (OSError, yaml.YAMLError) as e:
        violations.append(
            SkillpackViolation(
                path=rel_path / "manifest.yaml",
                rule="manifest-parse-error",
                message=str(e),
            )
        )
        return violations

    # Check manifest root is a mapping, not a sequence
    if not isinstance(manifest, dict):
        violations.append(
            SkillpackViolation(
                path=rel_path / "manifest.yaml",
                rule="manifest-root-mapping",
                message="Manifest root must be a mapping (dict), not a list or scalar",
            )
        )
        return violations

    # Validate required manifest sections
    required_sections = {
        "apiVersion": (str, "string"),
        "kind": (str, "string"),
        "metadata": (dict, "mapping"),
        "publisher": (dict, "mapping"),
        "source": (dict, "mapping"),
        "capability": (dict, "mapping"),
        "runtime": (dict, "mapping"),
        "permissions": (dict, "mapping"),
        "risk": (dict, "mapping"),
        "trust": (dict, "mapping"),
        "applicability": (dict, "mapping"),
        "autonomy": (dict, "mapping"),
        "evidence": (dict, "mapping"),
        "quality": (dict, "mapping"),
    }

    for section, (expected_type, type_name) in required_sections.items():
        if section not in manifest:
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule=f"manifest-missing-{section}",
                    message=f"Required section '{section}' ({type_name}) is missing",
                )
            )
        elif not isinstance(manifest[section], expected_type):
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule=f"manifest-invalid-{section}",
                    message=(
                        f"Section '{section}' must be a {type_name}, "
                        f"got {type(manifest[section]).__name__}"
                    ),
                )
            )

    # Built-in governance must be explicit. Do not let a missing field become
    # an implicit P0/L0/read-only default at parse or runtime time.
    applicability = manifest.get("applicability")
    if isinstance(applicability, dict):
        stages = applicability.get("project_stages")
        if not isinstance(stages, list) or not stages:
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="applicability-project-stages-invalid",
                    message="applicability.project_stages must be a non-empty string list",
                )
            )
        else:
            for index, stage in enumerate(stages):
                if not isinstance(stage, str) or stage not in VALID_LIFECYCLE_STAGES:
                    violations.append(
                        SkillpackViolation(
                            path=rel_path / "manifest.yaml",
                            rule="applicability-stage-invalid",
                            message=(
                                f"applicability.project_stages[{index}] must be one of "
                                f"{sorted(VALID_LIFECYCLE_STAGES)}, got {stage!r}"
                            ),
                        )
                    )

    autonomy = manifest.get("autonomy")
    if isinstance(autonomy, dict):
        ceiling = autonomy.get("ceiling")
        if ceiling not in VALID_AUTONOMY_CEILINGS:
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="autonomy-ceiling-invalid",
                    message=(
                        "autonomy.ceiling must be one of "
                        f"{sorted(VALID_AUTONOMY_CEILINGS)}, got {ceiling!r}"
                    ),
                )
            )
        side_effect_class = autonomy.get("side_effect_class")
        if side_effect_class not in VALID_SIDE_EFFECT_CLASSES:
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="autonomy-side-effect-class-invalid",
                    message=(
                        "autonomy.side_effect_class must be one of "
                        f"{sorted(VALID_SIDE_EFFECT_CLASSES)}, got {side_effect_class!r}"
                    ),
                )
            )

    evidence = manifest.get("evidence")
    if isinstance(evidence, dict):
        min_source_refs = evidence.get("min_source_refs")
        if (
            not isinstance(min_source_refs, int)
            or isinstance(min_source_refs, bool)
            or min_source_refs < 0
        ):
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="evidence-min-source-refs-invalid",
                    message="evidence.min_source_refs must be a non-negative integer",
                )
            )
        freshness_days = evidence.get("freshness_days")
        if freshness_days is not None and (
            not isinstance(freshness_days, int)
            or isinstance(freshness_days, bool)
            or freshness_days < 1
        ):
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="evidence-freshness-days-invalid",
                    message="evidence.freshness_days must be a positive integer when provided",
                )
            )
        if not isinstance(evidence.get("self_validation_forbidden"), bool):
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="evidence-self-validation-forbidden-invalid",
                    message="evidence.self_validation_forbidden must be a boolean",
                )
            )

    quality = manifest.get("quality")
    if isinstance(quality, dict):
        eval_suite = quality.get("eval_suite")
        eval_relative_path: Path | None = None
        if not isinstance(eval_suite, str) or not eval_suite.strip():
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="quality-eval-suite-invalid",
                    message="quality.eval_suite must be a non-empty path under evals/",
                )
            )
        else:
            eval_relative_path = Path(eval_suite)
            if (
                eval_relative_path.is_absolute()
                or ".." in eval_relative_path.parts
                or not eval_relative_path.parts
                or eval_relative_path.parts[0] != "evals"
            ):
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "manifest.yaml",
                        rule="quality-eval-suite-invalid",
                        message="quality.eval_suite must be a safe relative path under evals/",
                    )
                )
            elif not (root.parent / eval_relative_path).is_file():
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "manifest.yaml",
                        rule="quality-eval-suite-missing",
                        message=(
                            f"quality.eval_suite '{eval_suite}' is missing beside the "
                            "skillpacks bundle"
                        ),
                    )
                )

        negative_cases = quality.get("required_negative_cases")
        if (
            not isinstance(negative_cases, list)
            or not negative_cases
            or any(not isinstance(case, str) or not case.strip() for case in negative_cases)
        ):
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="quality-required-negative-cases-invalid",
                    message="quality.required_negative_cases must be a non-empty string list",
                )
            )

    # Check metadata.id exists
    if isinstance(manifest.get("metadata"), dict) and "id" not in manifest["metadata"]:
        violations.append(
            SkillpackViolation(
                path=rel_path / "manifest.yaml",
                rule="manifest-missing-metadata-id",
                message="metadata.id is required",
            )
        )

    # Check source.path exists
    if isinstance(manifest.get("source"), dict) and "path" not in manifest["source"]:
        violations.append(
            SkillpackViolation(
                path=rel_path / "manifest.yaml",
                rule="manifest-missing-source-path",
                message="source.path is required",
            )
        )

    # Check runtime.entrypoint
    if isinstance(manifest.get("runtime"), dict):
        if "entrypoint" not in manifest["runtime"]:
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="manifest-missing-entrypoint",
                    message="runtime.entrypoint is required",
                )
            )
        elif manifest["runtime"]["entrypoint"] != "SKILL.md":
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="entrypoint-invalid",
                    message=(
                        f"runtime.entrypoint must be 'SKILL.md', "
                        f"got '{manifest['runtime']['entrypoint']}'"
                    ),
                )
            )

        # Check runtime.tools is a list of strings
        if "tools" in manifest["runtime"]:
            tools = manifest["runtime"]["tools"]
            if not isinstance(tools, list):
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "manifest.yaml",
                        rule="runtime-tools-not-string-list",
                        message=f"runtime.tools must be a list, got {type(tools).__name__}",
                    )
                )
            else:
                for i, tool in enumerate(tools):
                    if not isinstance(tool, str):
                        violations.append(
                            SkillpackViolation(
                                path=rel_path / "manifest.yaml",
                                rule="runtime-tools-not-string-list",
                                message=(
                                    f"runtime.tools[{i}] must be a string, "
                                    f"got {type(tool).__name__}: {tool}"
                                ),
                            )
                        )

    # Check source.path matches pack directory
    if isinstance(manifest.get("source"), dict):
        source_path = manifest["source"].get("path")
        if source_path:
            # Normalize path: convert to POSIX, remove trailing slashes
            source_path_normalized = Path(source_path).as_posix().rstrip("/")
            pack_path_normalized = rel_path.as_posix().rstrip("/")

            # Ensure source path starts with skillpacks/
            if not source_path_normalized.startswith("skillpacks/"):
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "manifest.yaml",
                        rule="source-path-invalid",
                        message=(
                            f"source.path must be under skillpacks/, got '{source_path_normalized}'"
                        ),
                    )
                )
            elif source_path_normalized != f"skillpacks/{pack_path_normalized}":
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "manifest.yaml",
                        rule="source-path-mismatch",
                        message=(
                            f"source.path '{source_path_normalized}' does not match "
                            f"pack directory 'skillpacks/{pack_path_normalized}'"
                        ),
                    )
                )

    # Load and validate SKILL.md
    try:
        skillmd_text = skillmd_path.read_text()
    except OSError as e:
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule="skillmd-read-error",
                message=str(e),
            )
        )
        return violations

    # Parse frontmatter
    frontmatter, fm_error = _parse_skillmd_frontmatter(skillmd_text)

    if fm_error:
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule=fm_error,
                message="Failed to parse YAML frontmatter",
            )
        )
        return violations

    if not isinstance(frontmatter, dict):
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule="frontmatter-malformed",
                message="Frontmatter must be a mapping",
            )
        )
        return violations

    # Check frontmatter required fields
    if "name" not in frontmatter:
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule="frontmatter-missing-name",
                message="Frontmatter must contain 'name' field",
            )
        )
        return violations

    if "description" not in frontmatter:
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule="frontmatter-missing-description",
                message="Frontmatter must contain 'description' field",
            )
        )

    fm_name = frontmatter.get("name", "")
    if not isinstance(fm_name, str):
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule="frontmatter-invalid-name",
                message=f"Frontmatter 'name' must be a string, got {type(fm_name).__name__}",
            )
        )
        return violations

    # Check name normalization
    if isinstance(manifest.get("metadata"), dict):
        metadata_id = manifest["metadata"].get("id", "")
        if metadata_id:
            expected_name = normalize_discovery_name(metadata_id)
            if fm_name != expected_name:
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "SKILL.md",
                        rule="name-not-normalized",
                        message=(
                            f"Frontmatter 'name' is '{fm_name}', "
                            f"should be normalized form '{expected_name}' "
                            f"(from metadata.id '{metadata_id}')"
                        ),
                    )
                )

    # Tool contract validation
    declared_tools = set()
    if isinstance(manifest.get("runtime"), dict) and "tools" in manifest["runtime"]:
        tools_list = manifest["runtime"]["tools"]
        # Only collect valid string tools for contract checking
        # (invalid types already caught in tools validation above)
        for tool in tools_list:
            if isinstance(tool, str):
                declared_tools.add(tool)

    # Startup, sync and the CLI pass the actual plane inventory. Structural
    # unit fixtures may omit it when they are intentionally testing unrelated
    # manifest fields, but must inject a set to test tool registration.
    if registered_capabilities is not None:
        for tool in declared_tools:
            if tool not in registered_capabilities:
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "manifest.yaml",
                        rule="tool-not-registered",
                        message=(
                            f"Tool '{tool}' is declared in manifest.runtime.tools but is not "
                            "registered in the injected capability inventory"
                        ),
                    )
                )

    # Extract tools mentioned in SKILL.md
    allowed_tools = _extract_allowed_tools(skillmd_body=skillmd_text)
    referenced_capabilities = _extract_referenced_capabilities(skillmd_body=skillmd_text)

    for tool in declared_tools & referenced_capabilities:
        violations.append(
            SkillpackViolation(
                path=rel_path / "SKILL.md",
                rule="capability-callable-reference-overlap",
                message=(
                    f"Capability '{tool}' cannot be both an Allowed Tool Call and "
                    "a Referenced Capability (not callable)"
                ),
            )
        )

    # Check: every allowed tool must be declared
    for tool in allowed_tools:
        if tool not in declared_tools:
            violations.append(
                SkillpackViolation(
                    path=rel_path / "SKILL.md",
                    rule="tool-not-declared",
                    message=(
                        f"Tool '{tool}' is mentioned in Allowed Tool Calls "
                        f"but not declared in manifest.runtime.tools"
                    ),
                )
            )

    # Check: every declared tool must be used or marked optional
    for tool in declared_tools:
        if tool not in allowed_tools and not _is_tool_marked_optional(
            skillmd_body=skillmd_text, tool_id=tool
        ):
            violations.append(
                SkillpackViolation(
                    path=rel_path / "manifest.yaml",
                    rule="tool-declared-unused",
                    message=(
                        f"Tool '{tool}' is declared in manifest.runtime.tools "
                        f"but not mentioned in SKILL.md instructions "
                        f"(mark as optional with '(optional)' or 'nếu có' if intentional)"
                    ),
                )
            )

    # Attribution validation
    source_record = _extract_source_attribution_record(skillmd_text)
    if source_record and isinstance(source_record.get("upstream"), dict):
        upstream = source_record["upstream"]
        repo = upstream.get("repository")
        if repo and isinstance(repo, str) and repo.strip():
            commit = upstream.get("commit")
            if (
                not commit
                or not isinstance(commit, str)
                or not re.match(r"^[0-9a-fA-F]{40}$", commit.strip())
            ):
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "SKILL.md",
                        rule="attribution-invalid-commit",
                        message=(
                            f"SKILL.md ## Nguồn specifies upstream.repository '{repo}' "
                            f"but upstream.commit must be a 40-character hex SHA, got '{commit}'"
                        ),
                    )
                )

            license_val = upstream.get("license")
            if not license_val or not isinstance(license_val, str) or not license_val.strip():
                violations.append(
                    SkillpackViolation(
                        path=rel_path / "SKILL.md",
                        rule="attribution-missing-license",
                        message=(
                            f"SKILL.md ## Nguồn specifies upstream.repository '{repo}' "
                            f"but upstream.license is missing or empty"
                        ),
                    )
                )

            # Check matching entry in ledger if ledger is available
            ledger_path = _find_attribution_ledger(root)
            if ledger_path and ledger_path.exists():
                ledger = _parse_attribution_ledger(ledger_path)
                metadata_id = (
                    manifest.get("metadata", {}).get("id", "")
                    if isinstance(manifest.get("metadata"), dict)
                    else ""
                )
                if metadata_id not in ledger:
                    violations.append(
                        SkillpackViolation(
                            path=rel_path / "SKILL.md",
                            rule="attribution-ledger-missing",
                            message=(
                                f"Skill '{metadata_id}' has upstream attribution but is not "
                                f"recorded in attribution ledger '{ledger_path.name}'"
                            ),
                        )
                    )
                else:
                    ledger_entry = ledger[metadata_id]
                    valid_statuses = {"pending", "adapted", "published", "pinned", "retired"}
                    if ledger_entry.get("status") not in valid_statuses:
                        violations.append(
                            SkillpackViolation(
                                path=rel_path / "SKILL.md",
                                rule="attribution-ledger-status-invalid",
                                message=(
                                    f"Ledger entry for '{metadata_id}' has invalid status '{ledger_entry.get('status')}' "
                                    f"(expected one of {sorted(valid_statuses)})"
                                ),
                            )
                        )

    return violations
