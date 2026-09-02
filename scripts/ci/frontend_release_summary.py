#!/usr/bin/env python3
"""Task 11 — in tóm tắt GHOST route count cho job CI `frontend-integration`
(release-gate). Đọc snapshot generated (KHÔNG hand-edit, xem
`docs/architecture/generated/`), không tự tính lại route inventory ở đây —
chỉ đếm/hiển thị từ snapshot đã có sẵn (nguồn sự thật do
`scripts/route_inventory.py --check` bảo trì trong job `contract-freeze`).
"""

import json
import sys
from pathlib import Path

SNAPSHOT = Path("docs/architecture/generated/route-inventory.snapshot.json")


def main() -> int:
    if not SNAPSHOT.exists():
        print(f"MISSING {SNAPSHOT} — cannot report GHOST count.", file=sys.stderr)
        return 1
    snap = json.loads(SNAPSHOT.read_text())
    keys = snap.get("company_bound_keys", {})
    ghosts = sorted(
        k for k, v in keys.items() if not v.get("resolved") and not v.get("owner")
    )
    print(f"- total tracked routes: {len(keys)}")
    print(f"- GHOST (no handler, no allowlist owner): {len(ghosts)}")
    for g in ghosts:
        print(f"  - {g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
