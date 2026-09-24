#!/usr/bin/env python3
"""Ghi shared/contracts/executive-advisor-overlays.json từ AgentSpec overlay đã seed.

JSON là nguồn contract cho generator TS/Py; hash overlay/skill chỉ Python tính được
(canonical hash của AgentSpec), nên bước đồng bộ này chạy trước gen-executive-advisor-overlays.mjs.
`--check` báo lỗi nếu JSON lệch AgentSpec hiện tại (không ghi file).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "packages")]

from apps.cosa.agents.specs import EXECUTIVE_AGENT_SPECS  # noqa: E402

TARGET = ROOT / "shared/contracts/executive-advisor-overlays.json"
ROLES = ROOT / "shared/contracts/executive-advisor-roles.json"


def build() -> dict:
    roles = json.loads(ROLES.read_text(encoding="utf-8"))["roles"]
    overlays = []
    for role in roles:
        spec = EXECUTIVE_AGENT_SPECS[role["requiredAgentSpec"]]
        overlays.append(
            {
                "roleKey": role["key"],
                "overlaySpecId": spec.id,
                "overlaySpecVersion": spec.version,
                "overlayDefinitionHash": spec.definition_hash or spec.compute_hash(),
                "requiredProfileKey": role["requiredProfileKey"],
                "skillPins": [
                    {
                        "skillId": ref.skill_id,
                        "version": ref.version,
                        "definitionHash": ref.definition_hash,
                    }
                    for ref in spec.pinned_skills
                ],
                "advisoryOnly": True,
            }
        )
    return {"schemaVersion": 1, "overlays": overlays}


def main() -> int:
    content = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != content:
            print(
                f"{TARGET} lệch AgentSpec overlay; chạy scripts/sync_executive_advisor_overlays.py"
            )
            return 1
        return 0
    TARGET.write_text(content, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
