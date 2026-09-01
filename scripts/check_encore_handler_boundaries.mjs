#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const FORBIDDEN = ["drizzle-orm", "/models/db", "/db", "/shared/db/schema"];

function violationKey(file, line, moduleSpecifier) {
  return `${file}:${line}:HANDLER_DIRECT_DB:${moduleSpecifier}`;
}

function walkHandlerFiles(dir, callback) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (
      entry.name === "node_modules" ||
      entry.name === "dist" ||
      entry.name === ".encore" ||
      entry.name === ".git" ||
      entry.name === "tests" ||
      entry.name === "__tests__"
    ) {
      continue;
    }
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkHandlerFiles(fullPath, callback);
    } else if (
      entry.isFile() &&
      fullPath.endsWith(".handler.ts") &&
      !fullPath.endsWith(".d.ts") &&
      !fullPath.includes("/tests/") &&
      !fullPath.includes(".test.ts")
    ) {
      callback(fullPath);
    }
  }
}

export function findHandlerImports(rootDir) {
  const resolvedRoot = path.resolve(rootDir);
  const targetDirs = [
    path.join(resolvedRoot, "services", "company"),
    path.join(resolvedRoot, "services", "cosa"),
  ];

  const results = [];

  for (const targetDir of targetDirs) {
    walkHandlerFiles(targetDir, (filePath) => {
      const relFile = path.relative(resolvedRoot, filePath).replace(/\\/g, "/");
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const lineNum = i + 1;

        // Match import statements: import ... from '...'; or import '...';
        const importMatch = line.match(/^\s*import\s+(?:.*from\s+)?['"]([^'"]+)['"]/);
        if (!importMatch) continue;

        const moduleSpecifier = importMatch[1];
        results.push({
          file: relFile,
          line: lineNum,
          moduleSpecifier,
        });
      }
    });
  }

  return results;
}

export function readBaseline(baselinePath) {
  if (!baselinePath || !fs.existsSync(baselinePath)) {
    return { version: 1, entries: [] };
  }
  try {
    const raw = fs.readFileSync(baselinePath, "utf8");
    return JSON.parse(raw);
  } catch (err) {
    return { version: 1, entries: [] };
  }
}

export function runCheck({ rootDir = ".", baselinePath = null } = {}) {
  const resolvedRoot = path.resolve(rootDir);
  const imports = findHandlerImports(resolvedRoot);
  const observed = imports
    .filter(({ moduleSpecifier }) =>
      FORBIDDEN.some(
        (fragment) =>
          moduleSpecifier === fragment ||
          moduleSpecifier.includes(fragment) ||
          moduleSpecifier.endsWith(fragment)
      )
    )
    .map(({ file, line, moduleSpecifier }) => violationKey(file, line, moduleSpecifier))
    .sort();

  const baseline = baselinePath ? readBaseline(baselinePath) : { version: 1, entries: [] };
  const additions = observed.filter((entry) => !baseline.entries.includes(entry));
  const stale = baseline.entries.filter((entry) => !observed.includes(entry));

  return {
    observed,
    additions,
    stale,
  };
}

// CLI execution
const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename) {
  const args = process.argv.slice(2);
  let rootDir = ".";
  let baselinePath = null;
  let writeBaseline = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--root" && args[i + 1]) {
      rootDir = args[++i];
    } else if (args[i] === "--baseline" && args[i + 1]) {
      baselinePath = args[++i];
    } else if (args[i] === "--write-baseline") {
      writeBaseline = true;
    }
  }

  const { observed, additions, stale } = runCheck({ rootDir, baselinePath });

  if (writeBaseline) {
    if (!baselinePath) {
      console.error("Error: --write-baseline requires --baseline <path>");
      process.exit(1);
    }
    const data = {
      version: 1,
      entries: observed,
    };
    fs.writeFileSync(baselinePath, JSON.stringify(data, null, 2) + "\n", "utf8");
    console.log(`Wrote ${observed.length} baseline entries to ${baselinePath}`);
    process.exit(0);
  }

  let failed = false;

  if (additions.length > 0) {
    failed = true;
    console.error("❌ New Encore Handler DB Boundary Violations:");
    for (const add of additions) {
      console.error(`  + ${add}`);
    }
  }

  if (stale.length > 0) {
    failed = true;
    console.error("❌ Stale baseline entries (must be removed from baseline manifest):");
    for (const s of stale) {
      console.error(`  - ${s}`);
    }
  }

  if (failed) {
    process.exit(1);
  }

  console.log(`✅ Encore handler boundary check passed (${observed.length} baseline exceptions allowed).`);
  process.exit(0);
}
