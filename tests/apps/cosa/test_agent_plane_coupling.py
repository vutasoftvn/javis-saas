"""Test to identify all direct accesses to agent_plane attributes — baseline for decoupling."""

import re
import subprocess


def test_all_agent_plane_direct_accesses_documented():
    """Grep for direct access to agent_plane attributes across codebase."""
    result = subprocess.run(
        [
            "grep",
            "-E",
            "-r",
            r"plane\.(gateway|repository|policy_engine|approval_service|kernel|workflow)",
            "/Volumes/SSD/javis-saas/apps/cosa",
            "--include=*.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stdout.strip().split("\n")
    accessed_attrs = set()
    for line in lines:
        if not line:
            continue
        # Extract attribute names from patterns like "plane.gateway"
        match = re.search(r"plane\.(\w+)", line)
        if match:
            accessed_attrs.add(match.group(1))

    # Core attributes that will move to service interfaces
    core_usage = {"repository", "approval_service", "kernel"}
    assert core_usage.issubset(accessed_attrs), f"Core attributes not found: {core_usage - accessed_attrs}"
