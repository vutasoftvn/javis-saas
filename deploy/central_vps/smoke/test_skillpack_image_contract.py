from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "dockerfile",
    ["apps/cosa/Dockerfile.api", "apps/cosa/Dockerfile.worker"],
)
def test_cosa_runtime_image_copies_skillpack_bundle(dockerfile: str) -> None:
    """Runtime image phải tự mang bundle để bootstrap không cần checkout."""
    content = (REPO_ROOT / dockerfile).read_text(encoding="utf-8")

    assert "COPY skillpacks /app/skillpacks" in content
    assert "COPY evals /app/evals" in content
    assert (
        "COPY docs/integrations/skill-source-attribution.md "
        "/app/docs/integrations/skill-source-attribution.md"
    ) in content
