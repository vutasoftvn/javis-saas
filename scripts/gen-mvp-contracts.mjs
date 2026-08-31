#!/usr/bin/env node
// Generates MVP route/capability metadata for Company (TS), Agent Platform (Python), and Flutter (Dart)
// from the single source of truth: shared/contracts/mvp-surface.json
//
// Usage:
//   node scripts/gen-mvp-contracts.mjs          # Overwrite generated files
//   node scripts/gen-mvp-contracts.mjs --check  # CI: exit 1 if generated files are stale

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "shared/contracts/mvp-surface.json");
const CHECK = process.argv.includes("--check");

const raw = readFileSync(SRC, "utf8");
const manifest = JSON.parse(raw);

if (!Array.isArray(manifest.capabilities)) {
  console.error("Error: manifest.capabilities must be an array");
  process.exit(1);
}

// Validate unique IDs and method + path
const seenIds = new Set();
const seenRoutes = new Set();

for (const cap of manifest.capabilities) {
  if (!cap.id || typeof cap.id !== "string") {
    console.error(`Invalid capability: missing string id`, cap);
    process.exit(1);
  }
  if (seenIds.has(cap.id)) {
    console.error(`Duplicate capability id: ${cap.id}`);
    process.exit(1);
  }
  seenIds.add(cap.id);

  const routeKey = `${cap.plane}:${cap.method} ${cap.path}`;
  if (seenRoutes.has(routeKey)) {
    console.error(`Duplicate route: ${routeKey} on capability ${cap.id}`);
    process.exit(1);
  }
  seenRoutes.add(routeKey);
}

// Sort capabilities deterministically by id
const capabilities = [...manifest.capabilities].sort((a, b) => a.id.localeCompare(b.id));

const HEADER_LINES = [
  "GENERATED FILE — DO NOT MODIFY DIRECTLY",
  "Source: shared/contracts/mvp-surface.json · Generator: scripts/gen-mvp-contracts.mjs",
  "To update: edit shared/contracts/mvp-surface.json and run `node scripts/gen-mvp-contracts.mjs`",
];

const dartMember = (id) => {
  const parts = id.split(/[\._]/);
  return parts.map((w, i) => (i === 0 ? w : w[0].toUpperCase() + w.slice(1))).join("");
};

// ---- TypeScript -------------------------------------------------------------

function genTs() {
  const out = [];
  out.push(`/**\n * ${HEADER_LINES.join("\n * ")}\n */`);
  out.push("");
  out.push(`export type MvpPlane = "company" | "platform" | "agent" | "localWorker";`);
  out.push(`export type MvpSourceKind = "company_db" | "agent_db" | "object_store" | "control_plane" | "external_connector";`);
  out.push("");
  out.push(`export interface MvpCapabilityMetadata {`);
  out.push(`  readonly id: string;`);
  out.push(`  readonly enabled: boolean;`);
  out.push(`  readonly owner: string;`);
  out.push(`  readonly plane: MvpPlane;`);
  out.push(`  readonly method: string;`);
  out.push(`  readonly path: string;`);
  out.push(`  readonly schema: string;`);
  out.push(`  readonly sourceKind: MvpSourceKind;`);
  out.push(`  readonly requiresWorkspace: boolean;`);
  out.push(`  readonly frontendSymbol: string;`);
  out.push(`  readonly backendTest: string;`);
  out.push(`  readonly flutterTest: string;`);
  out.push(`  readonly integrationTest: string;`);
  out.push(`}`);
  out.push("");
  out.push(`export const MVP_CAPABILITIES: readonly MvpCapabilityMetadata[] = [`);

  for (const cap of capabilities) {
    const planeVal = cap.plane === "local_worker" ? "localWorker" : cap.plane;
    out.push(`  {`);
    out.push(`    id: ${JSON.stringify(cap.id)},`);
    out.push(`    enabled: ${Boolean(cap.enabled)},`);
    out.push(`    owner: ${JSON.stringify(cap.owner)},`);
    out.push(`    plane: ${JSON.stringify(planeVal)},`);
    out.push(`    method: ${JSON.stringify(cap.method)},`);
    out.push(`    path: ${JSON.stringify(cap.path)},`);
    out.push(`    schema: ${JSON.stringify(cap.schema)},`);
    out.push(`    sourceKind: ${JSON.stringify(cap.source_kind)},`);
    out.push(`    requiresWorkspace: ${Boolean(cap.requires_workspace)},`);
    out.push(`    frontendSymbol: ${JSON.stringify(cap.frontend_symbol || "")},`);
    out.push(`    backendTest: ${JSON.stringify(cap.backend_test || "")},`);
    out.push(`    flutterTest: ${JSON.stringify(cap.flutter_test || "")},`);
    out.push(`    integrationTest: ${JSON.stringify(cap.integration_test || "")},`);
    out.push(`  },`);
  }

  out.push(`] as const;`);
  out.push("");
  out.push(`export const MVP_CAPABILITY_BY_ID = new Map<string, MvpCapabilityMetadata>(`);
  out.push(`  MVP_CAPABILITIES.map((c) => [c.id, c])`);
  out.push(`);`);
  out.push("");
  return out.join("\n");
}

// ---- Python -----------------------------------------------------------------

function genPy() {
  const out = [];
  out.push(`"""\n${HEADER_LINES.join("\n")}\n"""`);
  out.push("from __future__ import annotations");
  out.push("");
  out.push("from dataclasses import dataclass");
  out.push("from typing import Literal, Final");
  out.push("");
  out.push(`MvpPlane = Literal["company", "platform", "agent", "localWorker"]`);
  out.push(`MvpSourceKind = Literal["company_db", "agent_db", "object_store", "control_plane", "external_connector"]`);
  out.push("");
  out.push("@dataclass(frozen=True)");
  out.push("class MvpCapabilityMetadata:");
  out.push("    id: str");
  out.push("    enabled: bool");
  out.push("    owner: str");
  out.push("    plane: MvpPlane");
  out.push("    method: str");
  out.push("    path: str");
  out.push("    schema: str");
  out.push("    source_kind: MvpSourceKind");
  out.push("    requires_workspace: bool");
  out.push("    frontend_symbol: str");
  out.push("    backend_test: str");
  out.push("    flutter_test: str");
  out.push("    integration_test: str");
  out.push("");
  out.push("MVP_CAPABILITIES: Final[tuple[MvpCapabilityMetadata, ...]] = (");

  for (const cap of capabilities) {
    const planeVal = cap.plane === "local_worker" ? "localWorker" : cap.plane;
    out.push("    MvpCapabilityMetadata(");
    out.push(`        id=${JSON.stringify(cap.id)},`);
    out.push(`        enabled=${cap.enabled ? "True" : "False"},`);
    out.push(`        owner=${JSON.stringify(cap.owner)},`);
    out.push(`        plane=${JSON.stringify(planeVal)},`);
    out.push(`        method=${JSON.stringify(cap.method)},`);
    out.push(`        path=${JSON.stringify(cap.path)},`);
    out.push(`        schema=${JSON.stringify(cap.schema)},`);
    out.push(`        source_kind=${JSON.stringify(cap.source_kind)},`);
    out.push(`        requires_workspace=${cap.requires_workspace ? "True" : "False"},`);
    out.push(`        frontend_symbol=${JSON.stringify(cap.frontend_symbol || "")},`);
    out.push(`        backend_test=${JSON.stringify(cap.backend_test || "")},`);
    out.push(`        flutter_test=${JSON.stringify(cap.flutter_test || "")},`);
    out.push(`        integration_test=${JSON.stringify(cap.integration_test || "")},`);
    out.push("    ),");
  }

  out.push(")");
  out.push("");
  out.push("MVP_CAPABILITY_BY_ID: Final[dict[str, MvpCapabilityMetadata]] = {");
  out.push("    cap.id: cap for cap in MVP_CAPABILITIES");
  out.push("}");
  out.push("");
  return out.join("\n");
}

// ---- Dart -------------------------------------------------------------------

function genDart() {
  const out = [];
  out.push(`// ${HEADER_LINES.join("\n// ")}`);
  out.push("");
  out.push("import 'api_result.dart';");
  out.push("");
  out.push("enum MvpEndpoint {");

  for (let i = 0; i < capabilities.length; i++) {
    const cap = capabilities[i];
    const member = dartMember(cap.id);
    const planeVal = cap.plane === "local_worker" || cap.plane === "localWorker"
      ? "ApiPlane.localWorker"
      : `ApiPlane.${cap.plane}`;

    out.push(`  ${member}(`);
    out.push(`    id: '${cap.id}',`);
    out.push(`    plane: ${planeVal},`);
    out.push(`    method: '${cap.method}',`);
    out.push(`    path: '${cap.path}',`);
    out.push(`    requiresWorkspace: ${Boolean(cap.requires_workspace)},`);
    out.push(`  )${i === capabilities.length - 1 ? ";" : ","}`);
  }

  out.push("");
  out.push("  const MvpEndpoint({");
  out.push("    required this.id,");
  out.push("    required this.plane,");
  out.push("    required this.method,");
  out.push("    required this.path,");
  out.push("    required this.requiresWorkspace,");
  out.push("  });");
  out.push("");
  out.push("  final String id;");
  out.push("  final ApiPlane plane;");
  out.push("  final String method;");
  out.push("  final String path;");
  out.push("  final bool requiresWorkspace;");
  out.push("");
  out.push("  static MvpEndpoint? fromId(String id) {");
  out.push("    for (final endpoint in MvpEndpoint.values) {");
  out.push("      if (endpoint.id == id) return endpoint;");
  out.push("    }");
  out.push("    return null;");
  out.push("  }");
  out.push("");
  out.push("  static MvpEndpoint byId(String id) {");
  out.push("    final endpoint = fromId(id);");
  out.push("    if (endpoint == null) {");
  out.push("      throw ArgumentError.value(id, 'id', 'Unknown MvpEndpoint ID');");
  out.push("    }");
  out.push("    return endpoint;");
  out.push("  }");
  out.push("}");
  out.push("");
  return out.join("\n");
}

// ---- Output Targets ---------------------------------------------------------

const TARGETS = [
  {
    path: join(ROOT, "services/company/shared/contracts/mvp-surface.generated.ts"),
    content: genTs(),
  },
  {
    path: join(ROOT, "apps/cosa/api/mvp_contracts_generated.py"),
    content: genPy(),
  },
  {
    path: join(ROOT, "frontend/lib/core/network/mvp_endpoints.g.dart"),
    content: genDart(),
  },
];

let hasDiff = false;

for (const target of TARGETS) {
  const dir = dirname(target.path);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  const existing = existsSync(target.path) ? readFileSync(target.path, "utf8") : "";
  if (existing !== target.content) {
    if (CHECK) {
      console.error(`[MVP-CONTRACTS-CHECK] File is out of date: ${target.path}`);
      hasDiff = true;
    } else {
      writeFileSync(target.path, target.content, "utf8");
      console.log(`[MVP-CONTRACTS-GEN] Updated ${target.path}`);
    }
  }
}

if (CHECK && hasDiff) {
  console.error("Please run `node scripts/gen-mvp-contracts.mjs` and commit the generated files.");
  process.exit(1);
}
