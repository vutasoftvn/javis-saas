#!/usr/bin/env python3
"""Extract the Founder Trial R1 baseline DDL from a pg_dump --schema-only file.

Emits, for a given allowlist of `schema.table` names:
  CREATE SCHEMA (for every retained schema)
  CREATE TABLE ... (verbatim, incl. inline CHECK constraints)
  ALTER TABLE ... ADD CONSTRAINT ...  (PK / UNIQUE / FK — FK kept only when the
                                       referenced table is also retained)
  CREATE [UNIQUE] INDEX ... (only on retained tables)

Sequences: pg_dump uses `id bigint NOT NULL` with a separate identity/sequence;
the app schemas here use application-generated Snowflake ids (plain bigint), so
no sequence handling is needed.
"""
import re
import sys

DUMP, OUT, *rest = sys.argv[1:]
# Optional --universe a.b,c.d  = tables that exist (from earlier migration
# groups) and so an FK may still point at them, even though this file does not
# (re)create them.
universe_extra = set()
if rest and rest[0] == "--universe":
    universe_extra = set(rest[1].split(","))
    rest = rest[2:]
ALLOW = rest
allow = set(ALLOW)  # tables THIS file creates
schemas = sorted({a.split(".")[0] for a in allow})

src = open(DUMP).read()

# ---- CREATE TABLE blocks ---------------------------------------------------
tables = {}
for m in re.finditer(r"^CREATE TABLE (\w+)\.(\w+) \(\n(.*?)^\);\n", src, re.S | re.M):
    sch, tbl, body = m.group(1), m.group(2), m.group(3)
    if f"{sch}.{tbl}" in allow:
        tables[f"{sch}.{tbl}"] = f"CREATE TABLE {sch}.{tbl} (\n{body});\n"

# ---- ALTER TABLE ... ADD CONSTRAINT --------------------------------------
constraints = {k: [] for k in allow}
for m in re.finditer(
    r"^ALTER TABLE ONLY (\w+)\.(\w+)\n\s+ADD CONSTRAINT (.*?);\n", src, re.S | re.M
):
    sch, tbl, cdef = m.group(1), m.group(2), m.group(3).strip()
    key = f"{sch}.{tbl}"
    if key not in allow:
        continue
    fk = re.search(r"REFERENCES (\w+)\.(\w+)", cdef)
    if fk and f"{fk.group(1)}.{fk.group(2)}" not in (allow | universe_extra):
        continue  # drop FK to a non-retained table
    constraints[key].append(
        f"ALTER TABLE ONLY {sch}.{tbl} ADD CONSTRAINT {cdef};\n"
    )

# ---- CREATE INDEX ------------------------------------------------------------
indexes = {k: [] for k in allow}
for m in re.finditer(
    r"^CREATE (?:UNIQUE )?INDEX \w+ ON (\w+)\.(\w+) .*?;\n", src, re.M
):
    key = f"{m.group(1)}.{m.group(2)}"
    if key in allow:
        indexes[key].append(m.group(0))

# ---- order tables so FK targets come first --------------------------------
dep = {k: set() for k in tables}
for k, cs in constraints.items():
    for c in cs:
        fk = re.search(r"REFERENCES (\w+\.\w+)", c)
        if fk and fk.group(1) in tables and fk.group(1) != k:
            dep[k].add(fk.group(1))
ordered, seen = [], set()
def visit(n):
    if n in seen:
        return
    seen.add(n)
    for d in sorted(dep.get(n, ())):
        visit(d)
    ordered.append(n)
for k in sorted(tables):
    visit(k)

# ---- emit -----------------------------------------------------------------
out = ["-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,",
       "-- then filtered to the Founder Trial R1 retained allowlist. Review before use.",
       "-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md",
       ""]
for s in schemas:
    out.append(f"CREATE SCHEMA IF NOT EXISTS {s};")
out.append("")
for k in ordered:
    out.append(tables[k])
    out.extend(constraints[k])
    out.extend(indexes[k])
    out.append("")

open(OUT, "w").write("\n".join(out))
missing = allow - set(tables)
print(f"{OUT}: {len(tables)} tables, "
      f"{sum(len(v) for v in constraints.values())} constraints, "
      f"{sum(len(v) for v in indexes.values())} indexes"
      + (f"  MISSING: {sorted(missing)}" if missing else ""))
