#!/usr/bin/env node
// Sinh mã enum canonical cho 3 runtime từ một nguồn duy nhất: shared/contracts/enums.json
//
//   node scripts/gen-contracts.mjs           # ghi đè file generated
//   node scripts/gen-contracts.mjs --check   # CI: fail nếu file generated lệch nguồn
//
// Nguồn sự thật: shared/contracts/enums.json (M0 contract freeze).
// Xem docs/architecture/plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "shared/contracts/enums.json");
const CHECK = process.argv.includes("--check");

const spec = JSON.parse(readFileSync(SRC, "utf8"));
const enums = spec.enums;
const maps = spec.migration_maps;

const HEADER_LINES = [
  "GENERATED — KHÔNG SỬA TAY.",
  "Nguồn: shared/contracts/enums.json · Sinh bởi: scripts/gen-contracts.mjs",
  "Đổi enum ⇒ sửa JSON nguồn rồi chạy `node scripts/gen-contracts.mjs` và commit.",
];

// ---- helpers ---------------------------------------------------------------

const pascal = (snake) =>
  snake.split("_").map((w) => w[0].toUpperCase() + w.slice(1).toLowerCase()).join("");
const camel = (s) => {
  const p = pascal(s);
  return p[0].toLowerCase() + p.slice(1);
};
// W0_IDEA -> w0Idea ; PRODUCT_MARKET_FIT -> productMarketFit
const dartMember = (value) => {
  const parts = value.toLowerCase().split("_");
  return parts
    .map((w, i) => (i === 0 ? w : w[0].toUpperCase() + w.slice(1)))
    .join("");
};

// ---- TypeScript ----------------------------------------------------------

function genTs() {
  const out = [];
  out.push(`/**\n * ${HEADER_LINES.join("\n * ")}\n */`);
  out.push("");
  for (const [name, def] of Object.entries(enums)) {
    const T = pascal(name);
    const CONST = name.toUpperCase();
    out.push(`/** ${def.doc} */`);
    out.push(
      `export const ${CONST} = [${def.values.map((v) => JSON.stringify(v)).join(", ")}] as const;`
    );
    out.push(`export type ${T} = (typeof ${CONST})[number];`);
    out.push(`export function is${T}(v: unknown): v is ${T} {`);
    out.push(`  return typeof v === "string" && (${CONST} as readonly string[]).includes(v);`);
    out.push(`}`);
    out.push(`export function parse${T}(v: string): ${T} {`);
    out.push(`  if (!is${T}(v)) throw new Error(\`Unknown ${T} wire value: \${v}\`);`);
    out.push(`  return v;`);
    out.push(`}`);
    out.push("");
  }
  for (const [name, table] of Object.entries(maps)) {
    if (name.startsWith("_")) continue;
    const CONST = name.toUpperCase();
    out.push(
      `export const ${CONST}: Readonly<Record<string, string>> = Object.freeze(${JSON.stringify(
        table
      )});`
    );
  }
  out.push("");
  return out.join("\n");
}

// ---- Dart ---------------------------------------------------------------

function genDart() {
  const out = [];
  out.push(`// ${HEADER_LINES.join("\n// ")}`);
  out.push("// ignore_for_file: constant_identifier_names, lines_longer_than_80_chars");
  out.push("");
  for (const [name, def] of Object.entries(enums)) {
    const T = pascal(name);
    out.push(`/// ${def.doc}`);
    out.push(`enum ${T} {`);
    out.push(
      def.values.map((v) => `  ${dartMember(v)}('${v}')`).join(",\n") + ";"
    );
    out.push("");
    out.push(`  const ${T}(this.wire);`);
    out.push(`  final String wire;`);
    out.push("");
    out.push(`  static ${T} fromWire(String v) => values.firstWhere(`);
    out.push(`        (e) => e.wire == v,`);
    out.push(
      `        orElse: () => throw ArgumentError('Unknown ${T} wire value: \$v'),`
    );
    out.push(`      );`);
    out.push("");
    out.push(`  static ${T}? tryFromWire(String? v) {`);
    out.push(`    if (v == null) return null;`);
    out.push(`    for (final e in values) {`);
    out.push(`      if (e.wire == v) return e;`);
    out.push(`    }`);
    out.push(`    return null;`);
    out.push(`  }`);
    out.push("");
    out.push(`  String toApi() => wire;`);
    out.push(`}`);
    out.push("");
  }
  for (const [name, table] of Object.entries(maps)) {
    if (name.startsWith("_")) continue;
    const cn = camel(name);
    out.push(`const Map<String, String> ${cn} = {`);
    out.push(
      Object.entries(table)
        .map(([k, v]) => `  '${k}': '${v}',`)
        .join("\n")
    );
    out.push(`};`);
    out.push("");
  }
  return out.join("\n");
}

// ---- Python -----------------------------------------------------------

function genPy() {
  const out = [];
  out.push(`"""${HEADER_LINES.join("\n")}\n"""`);
  out.push("");
  out.push("from __future__ import annotations");
  out.push("");
  out.push("from enum import StrEnum");
  out.push("");
  const allNames = [
    ...Object.keys(enums).map((n) => pascal(n)),
    ...Object.keys(maps)
      .filter((n) => !n.startsWith("_"))
      .map((n) => n.toUpperCase()),
  ].sort((a, b) => a.localeCompare(b)); // ruff RUF022: __all__ sorted
  out.push("__all__ = [");
  for (const n of allNames) out.push(`    "${n}",`);
  out.push("]");
  out.push("");
  out.push("");
  for (const [name, def] of Object.entries(enums)) {
    const T = pascal(name);
    out.push(`class ${T}(StrEnum):`);
    out.push(`    """${def.doc}"""`);
    out.push("");
    for (const v of def.values) out.push(`    ${v} = "${v}"`);
    out.push("");
    out.push(`    @classmethod`);
    out.push(`    def from_wire(cls, v: str) -> ${T}:`);
    out.push(`        try:`);
    out.push(`            return cls(v)`);
    out.push(`        except ValueError as exc:  # pragma: no cover - thông điệp lỗi`);
    out.push(
      `            raise ValueError(f"Unknown ${T} wire value: {v!r}") from exc`
    );
    out.push("");
    out.push(`    def to_wire(self) -> str:`);
    out.push(`        return self.value`);
    out.push("");
    out.push("");
  }
  for (const [name, table] of Object.entries(maps)) {
    if (name.startsWith("_")) continue;
    out.push(`${name.toUpperCase()}: dict[str, str] = {`);
    for (const [k, v] of Object.entries(table)) out.push(`    "${k}": "${v}",`);
    out.push(`}`);
    out.push("");
  }
  return out.join("\n");
}

// ---- write / check ----------------------------------------------------

const artifacts = [
  ["services/company/shared/contracts/enums.generated.ts", genTs()],
  ["services/cosa/shared/contracts/enums.generated.ts", genTs()],
  ["frontend/lib/core/contracts/enums.generated.dart", genDart()],
  ["packages/agent/contracts/enums_generated.py", genPy()],
];

let drift = false;
for (const [rel, content] of artifacts) {
  const abs = join(ROOT, rel);
  let current = null;
  try {
    current = readFileSync(abs, "utf8");
  } catch {
    /* chưa tồn tại */
  }
  if (current === content) continue;
  if (CHECK) {
    drift = true;
    console.error(`DRIFT: ${rel} lệch nguồn shared/contracts/enums.json`);
  } else {
    mkdirSync(dirname(abs), { recursive: true });
    writeFileSync(abs, content);
    console.log(`wrote ${rel}`);
  }
}

if (CHECK) {
  if (drift) {
    console.error("\nChạy `node scripts/gen-contracts.mjs` rồi commit lại.");
    process.exit(1);
  }
  console.log("contracts generated code in sync ✓");
}
