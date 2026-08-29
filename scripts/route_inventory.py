#!/usr/bin/env python3
"""M0 contract freeze — route inventory + drift snapshot lint.

    python scripts/route_inventory.py            # regenerate doc + snapshot
    python scripts/route_inventory.py --check    # CI: fail on undeclared route drift

Nguồn intent: docs/architecture/plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md §3.

Cách tiếp cận: KHÔNG cố phân loại toàn bộ 200+ call site nội suy chuỗi. Thay vào đó:
  1. Sinh tài liệu inventory hai phía (Encore handlers + frontend call sites + AgentOS routes) — thông tin.
  2. Snapshot tập `"<METHOD> <static-prefix>"` của frontend. CI fail nếu xuất hiện key MỚI mà:
       - không khớp prefix 2 đoạn của bất kỳ handler nào, VÀ
       - không nằm trong allowlist "known-broken, owned by M4/M7".
     Đây chính là "snapshot test" ở M0 test plan.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "docs/architecture/generated"
DOC = GEN / "route-inventory.md"
SNAPSHOT = GEN / "route-inventory.snapshot.json"
ALLOWLIST = GEN / "route-inventory.allowlist.json"

SERVICE_TS_DIRS = [ROOT / "services/company", ROOT / "services/cosa"]
FRONTEND_LIB = ROOT / "frontend/lib"
AGENTOS_DIRS = [ROOT / "apps/cosa"]

# --- normalizeEndpoint (frontend/lib/core/network/api_client.dart) rút gọn ---
# Chỉ các rewrite ảnh hưởng tới việc route có tới Company Encore base hay không.
NORMALIZE_PREFIX_REWRITES = [
    ("/api/v1/auth/", "/identity/"),
    ("/auth/", "/identity/"),
    ("/api/v1/tasks", "/operations/tasks"),
    ("/tasks", "/operations/tasks"),
    ("/api/v1/sales/", "/commercial/"),
    ("/sales/", "/commercial/"),
    ("/api/v1/finance/", "/finance-legal/"),
    ("/finance/", "/finance-legal/"),
    ("/api/v1/legal/", "/finance-legal/"),
    ("/legal/", "/finance-legal/"),
    ("/api/v1/marketing/context", "/commercial/marketing-context"),
    ("/marketing/context", "/commercial/marketing-context"),
    ("/api/v1/skills", "/agent/skills"),
    ("/skills", "/agent/skills"),
]
# Prefix (sau normalize) KHÔNG nhắm tới Company Encore base ⇒ bỏ khỏi drift lint.
NON_COMPANY_PREFIXES = ("/platform", "/agent/", "/agents", "/agent?", "/local-worker/", "/ai/", "/ai?")

HANDLER_RE = re.compile(r'\bpath:\s*["\'](/[^"\']+)["\']')
HANDLER_META_RE = re.compile(r'\b(method|expose|auth):\s*(?:["\'](\w+)["\']|(true|false))')
FRONT_CALL_RE = re.compile(
    r'ApiClient\.(get|post|put|patch|delete)\(\s*[\'"]([^\'"$?{]+)'
)
AGENTOS_RE = re.compile(
    r'@(?:app|router)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']'
)


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def collect_handlers() -> list[dict]:
    out: list[dict] = []
    for base in SERVICE_TS_DIRS:
        for f in base.rglob("*.ts"):
            if "node_modules" in f.parts or f.name.endswith(".test.ts"):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(
                r'api(?:\.raw)?\(\s*\{([^}]*)\}', text, re.DOTALL
            ):
                block = m.group(1)
                pm = HANDLER_RE.search(block)
                if not pm:
                    continue
                meta = {"method": "GET", "expose": False, "auth": False}
                for mm in HANDLER_META_RE.finditer(block):
                    key = mm.group(1)
                    val = mm.group(2) or mm.group(3)
                    meta[key] = val if key == "method" else (val == "true")
                out.append(
                    {
                        "method": str(meta["method"]).upper(),
                        "path": pm.group(1),
                        "service": base.name,
                        "expose": bool(meta["expose"]),
                        "auth": bool(meta["auth"]),
                        "file": _rel(f),
                    }
                )
    out.sort(key=lambda r: (r["path"], r["method"]))
    return out


def normalize_prefix(path: str) -> str:
    for src, dst in NORMALIZE_PREFIX_REWRITES:
        if path == src or path.startswith(src):
            return dst + path[len(src):]
    return path


def collect_frontend() -> list[dict]:
    out: list[dict] = []
    for f in FRONTEND_LIB.rglob("*.dart"):
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in FRONT_CALL_RE.finditer(line):
                method, raw = m.group(1).upper(), m.group(2)
                prefix = normalize_prefix(raw.rstrip("/") or raw)
                out.append(
                    {"method": method, "raw": raw, "prefix": prefix, "file": _rel(f), "line": i}
                )
    out.sort(key=lambda r: (r["prefix"], r["method"], r["file"]))
    return out


def collect_agentos() -> list[dict]:
    out: list[dict] = []
    for base in AGENTOS_DIRS:
        for f in base.rglob("*.py"):
            if "test" in f.name:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in AGENTOS_RE.finditer(text):
                out.append(
                    {"method": m.group(1).upper(), "path": m.group(2), "file": _rel(f)}
                )
    out.sort(key=lambda r: (r["path"], r["method"]))
    return out


def two_seg(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    return "/" + "/".join(parts[:2])


def is_company_bound(prefix: str) -> bool:
    return not prefix.startswith(NON_COMPANY_PREFIXES)


def resolve(prefix: str, method: str, handler_prefixes: set[str]) -> bool:
    return two_seg(prefix) in handler_prefixes


def build() -> dict:
    handlers = collect_handlers()
    frontend = collect_frontend()
    agentos = collect_agentos()
    allow = json.loads(ALLOWLIST.read_text()) if ALLOWLIST.exists() else {}
    allow = {k: v for k, v in allow.items() if not k.startswith("_")}

    handler_2seg = {two_seg(h["path"]) for h in handlers}

    keys: dict[str, dict] = {}
    for c in frontend:
        if not is_company_bound(c["prefix"]):
            continue
        key = f'{c["method"]} {c["prefix"]}'
        if key in keys:
            keys[key]["sites"].append(f'{c["file"]}:{c["line"]}')
            continue
        resolved = resolve(c["prefix"], c["method"], handler_2seg)
        keys[key] = {
            "resolved": resolved,
            "owner": allow.get(key),
            "sites": [f'{c["file"]}:{c["line"]}'],
        }

    return {
        "handlers": handlers,
        "frontend": frontend,
        "agentos": agentos,
        "company_bound_keys": dict(sorted(keys.items())),
        "allow": allow,
    }


def render_doc(data: dict) -> str:
    L = ["# Route inventory (GENERATED — `scripts/route_inventory.py`)", ""]
    L.append("Nguồn intent: [M0 §3](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md).")
    L.append("Không sửa tay. Chạy `make route-inventory` để cập nhật; `make route-inventory-check` ở CI.")
    L.append("")
    L.append("## 1. Encore handler routes (`services/company`, `services/cosa`)")
    L.append("")
    L.append("| Method | Path | Service | expose | auth | File |")
    L.append("|---|---|---|---|---|---|")
    for h in data["handlers"]:
        L.append(
            f'| {h["method"]} | `{h["path"]}` | {h["service"]} | '
            f'{"✓" if h["expose"] else ""} | {"✓" if h["auth"] else ""} | {h["file"]} |'
        )
    L.append("")
    L.append("### ⚠ `expose:true` không `auth` (rà M1)")
    L.append("")
    danger = [h for h in data["handlers"] if h["expose"] and not h["auth"]]
    for h in danger:
        L.append(f'- {h["method"]} `{h["path"]}` — {h["file"]}')
    if not danger:
        L.append("- (không có)")
    L.append("")
    L.append("## 2. Frontend company-bound call sites — trạng thái resolve")
    L.append("")
    L.append("| Key (METHOD prefix) | Resolved | Owner (allowlist) | Call sites |")
    L.append("|---|---|---|---|")
    for key, v in data["company_bound_keys"].items():
        sites = ", ".join(v["sites"][:3]) + (" …" if len(v["sites"]) > 3 else "")
        L.append(
            f'| `{key}` | {"✓" if v["resolved"] else "✗ GHOST"} | {v["owner"] or ""} | {sites} |'
        )
    L.append("")
    L.append("## 3. Known-broken allowlist (route ma đã biết — owned by M4/M7)")
    L.append("")
    L.append("| Key | Owner milestone |")
    L.append("|---|---|")
    for key, owner in sorted(data["allow"].items()):
        L.append(f"| `{key}` | {owner} |")
    L.append("")
    L.append("## 4. AgentOS FastAPI routes (`apps/cosa`) — tham chiếu, không thuộc drift lint")
    L.append("")
    L.append("| Method | Path | File |")
    L.append("|---|---|---|")
    for r in data["agentos"]:
        L.append(f'| {r["method"]} | `{r["path"]}` | {r["file"]} |')
    L.append("")
    L.append("## 5. `normalizeEndpoint` rewrites gây route drift (M7 gỡ dần)")
    L.append("")
    for src, dst in NORMALIZE_PREFIX_REWRITES:
        L.append(f"- `{src}*` → `{dst}*`")
    L.append("")
    return "\n".join(L)


def snapshot_view(data: dict) -> dict:
    return {
        "_meta": "GENERATED snapshot cho route drift lint (M0). Cập nhật: make route-inventory.",
        "company_bound_keys": {
            k: {"resolved": v["resolved"], "owner": v["owner"]}
            for k, v in data["company_bound_keys"].items()
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    data = build()
    doc = render_doc(data)
    snap = snapshot_view(data)

    if not args.check:
        DOC.write_text(doc + "\n")
        SNAPSHOT.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n")
        if not ALLOWLIST.exists():
            ALLOWLIST.write_text("{}\n")
        print(f"wrote {_rel(DOC)}")
        print(f"wrote {_rel(SNAPSHOT)}")
        return 0

    # --- check mode ---
    if not SNAPSHOT.exists():
        print("MISSING snapshot — chạy `make route-inventory` và commit.", file=sys.stderr)
        return 1
    prev = json.loads(SNAPSHOT.read_text())["company_bound_keys"]
    curr = snap["company_bound_keys"]
    fail = False

    added = sorted(set(curr) - set(prev))
    removed = sorted(set(prev) - set(curr))
    for key in added:
        v = curr[key]
        if v["resolved"] or v["owner"]:
            print(f"NOTE route mới (khớp handler hoặc allowlist): {key}", file=sys.stderr)
            fail = True  # vẫn cần commit snapshot mới
        else:
            print(f"GHOST route mới không handler, không allowlist: {key}", file=sys.stderr)
            fail = True
    for key in removed:
        print(f"NOTE route đã bỏ (cần cập nhật snapshot): {key}", file=sys.stderr)
        fail = True
    # regression: một key đang resolved chuyển thành ghost
    for key in set(prev) & set(curr):
        if prev[key]["resolved"] and not curr[key]["resolved"] and not curr[key]["owner"]:
            print(f"REGRESSION route mất handler: {key}", file=sys.stderr)
            fail = True

    if fail:
        print("\nChạy `make route-inventory`, review, rồi commit snapshot.", file=sys.stderr)
        return 1
    print("route inventory in sync ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
