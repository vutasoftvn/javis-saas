from pathlib import Path

import yaml


DATA_ROOT = Path(__file__).parents[4] / "regulations" / "vn" / "tt58_2026"


def get_book_templates(mode: str) -> list[dict]:
    data = yaml.safe_load((DATA_ROOT / "modes.yaml").read_text())
    return list(data.get("modes", {}).get(mode, {}).get("books", []))
