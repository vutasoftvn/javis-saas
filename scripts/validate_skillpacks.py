#!/usr/bin/env python3
"""
Command-line validator for skillpacks.

Resolves repo root relative to this script, validates all skillpacks,
and prints violations in the format: path:rule:message

Optional: --root <path> to override skillpacks directory (for testing).
Default: repo_root / "skillpacks"
"""

import argparse
import sys
from pathlib import Path


def find_repo_root() -> Path:
    """Walk up from this script to find repo root."""
    current = Path(__file__).parent.parent
    while current != current.parent:
        if (current / "packages").exists() and (current / "skillpacks").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repo root")


def main() -> int:
    """Validate skillpacks and print violations."""
    try:
        parser = argparse.ArgumentParser(
            description="Validate skillpack contracts",
            prog="validate_skillpacks.py"
        )
        parser.add_argument(
            "--root",
            type=Path,
            default=None,
            help="Path to skillpacks directory to validate (default: repo_root/skillpacks)"
        )
        args = parser.parse_args()

        repo_root = find_repo_root()

        # Use provided --root or default to repo_root/skillpacks
        if args.root:
            skillpacks_dir = Path(args.root)
        else:
            skillpacks_dir = repo_root / "skillpacks"

        # Add repo root and packages to sys.path so imports work
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        if str(repo_root / "packages") not in sys.path:
            sys.path.insert(0, str(repo_root / "packages"))

        # Dynamic import to handle module path
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "skillpack_contract",
            repo_root / "packages" / "agent_core" / "skills" / "skillpack_contract.py"
        )
        skillpack_contract = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(skillpack_contract)

        validate_skillpack_tree = skillpack_contract.validate_skillpack_tree

        violations = validate_skillpack_tree(skillpacks_dir)

        for violation in violations:
            print(f"{violation.path}:{violation.rule}:{violation.message}")

        return 0 if not violations else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
