#!/usr/bin/env python3
"""M0 contract freeze — Company read/write usage inventory.

    python scripts/company_usage_inventory.py           # regenerate doc
    python scripts/company_usage_inventory.py --check    # CI: fail nếu doc lệch

Phân loại mọi occurrence `company` / `companyId` / `company_id` thành:
  - LEGACY_TENANCY  : Company aggregate/tenant song song Workspace — M2 xóa.
  - VALID_KEEP      : tên công ty của customer/counterparty trong CRM/commercial, doc tiếng Anh.
  - REVIEW          : chưa phân loại — cần review thủ công khi M2 chạm file.

Xem docs/architecture/plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md §4.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/architecture/generated/company-usage-inventory.md"

SCAN_DIRS = ["services", "apps", "packages", "frontend/lib", "landing/src"]
EXCLUDE_PARTS = {"node_modules", "build", ".dart_tool", "encore.gen", "__pycache__"}
EXCLUDE_SUFFIX = (".lock", ".map")
PATTERN = re.compile(r"company", re.IGNORECASE)

# --- luật phân loại theo path (khớp lần lượt, dừng ở match đầu) ---
LEGACY_TENANCY_PATHS = [
    "services/cosa/storage/schema.ts",
    "services/cosa/services/auth.service.ts",
    "services/cosa/handlers/company.handler.ts",
    "services/cosa/services/agent-policy.service.ts",
    "services/cosa/services/company",
    "services/company/identity/services/sync.service.ts",
    "services/company/identity/services/workspace.service.ts",
]
LEGACY_TENANCY_TOKENS = [
    "company_memberships",
    "company_membership",
    "company_agent_policy",
    "company_entitlements",
    "join_company_id",
    "company_name",
    "companyStage",
    "company_stage",
    "platformCompanyId",
    "platform_company_id",
    "venture_stage_entered_at",
    "ventureStage",
]
VALID_KEEP_PATH_SUBSTR = [
    "services/company/commercial/",
    "services/company/shared/db/schema/commercial.ts",
    "services/company/shared/db/schema/customer-engagement.ts",
    "frontend/lib/modules/sales/",
    "frontend/lib/modules/marketing/",
    "landing/",
    "/customer-engagement/",
]
VALID_KEEP_TOKENS = [
    "companyName",  # tên hiển thị của khách hàng/đối tác
    "company_size",
    "companySize",
    "target company",
    "counterparty",
]


def classify(rel: str, line: str) -> str:
    low = line.lower()
    for tok in LEGACY_TENANCY_TOKENS:
        if tok.lower() in low:
            return "LEGACY_TENANCY"
    for p in LEGACY_TENANCY_PATHS:
        if rel.startswith(p):
            return "LEGACY_TENANCY"
    for tok in VALID_KEEP_TOKENS:
        if tok.lower() in low:
            return "VALID_KEEP"
    for sub in VALID_KEEP_PATH_SUBSTR:
        if sub in rel:
            return "VALID_KEEP"
    return "REVIEW"


def iter_files():
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            if EXCLUDE_PARTS & set(f.parts):
                continue
            if f.suffix in EXCLUDE_SUFFIX or f.name.endswith(".test.ts"):
                continue
            if ".generated." in f.name or f.name.endswith("_generated.py"):
                continue  # mã sinh — banned-alias text trong comment không phải usage thật
            if f.suffix not in {".ts", ".tsx", ".dart", ".py", ".sql", ".json"}:
                continue
            yield f


def build() -> dict:
    buckets: dict[str, dict[str, int]] = {
        "LEGACY_TENANCY": {},
        "VALID_KEEP": {},
        "REVIEW": {},
    }
    totals = {"LEGACY_TENANCY": 0, "VALID_KEEP": 0, "REVIEW": 0}
    for f in iter_files():
        rel = str(f.relative_to(ROOT))
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not PATTERN.search(line):
                continue
            cls = classify(rel, line)
            buckets[cls][rel] = buckets[cls].get(rel, 0) + 1
            totals[cls] += 1
    return {"buckets": buckets, "totals": totals}


def render(data: dict) -> str:
    t = data["totals"]
    L = [
        "# Company usage inventory (GENERATED — `scripts/company_usage_inventory.py`)",
        "",
        "Nguồn intent: [M0 §4](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md).",
        "Phân loại heuristic theo path + token. `REVIEW` = cần mắt người khi M2 chạm file.",
        "",
        f"| Lớp | Occurrences | Files |",
        "|---|---|---|",
        f"| LEGACY_TENANCY (M2 xóa) | {t['LEGACY_TENANCY']} | {len(data['buckets']['LEGACY_TENANCY'])} |",
        f"| VALID_KEEP (giữ nguyên) | {t['VALID_KEEP']} | {len(data['buckets']['VALID_KEEP'])} |",
        f"| REVIEW (chưa phân loại) | {t['REVIEW']} | {len(data['buckets']['REVIEW'])} |",
        "",
    ]
    for cls, title in [
        ("LEGACY_TENANCY", "Legacy tenancy — M2 xóa Company aggregate"),
        ("REVIEW", "Cần review thủ công (M2)"),
        ("VALID_KEEP", "Hợp lệ — customer/counterparty company name, giữ nguyên"),
    ]:
        L.append(f"## {title}")
        L.append("")
        L.append("| File | Hits |")
        L.append("|---|---|")
        for rel, n in sorted(data["buckets"][cls].items(), key=lambda kv: (-kv[1], kv[0])):
            L.append(f"| {rel} | {n} |")
        L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    doc = render(build()) + "\n"
    if args.check:
        if not DOC.exists() or DOC.read_text() != doc:
            print("company-usage-inventory.md lệch — chạy `make company-usage-inventory` và commit.", file=sys.stderr)
            return 1
        print("company usage inventory in sync ✓")
        return 0
    DOC.write_text(doc)
    print(f"wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
