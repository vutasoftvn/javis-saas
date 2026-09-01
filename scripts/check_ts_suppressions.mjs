#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DIRECTIVES = ["@ts-ignore", "@ts-expect-error"];
const DIRECTIVE_REGEX = /^\s*\/\/\s*@(ts-ignore|ts-expect-error)\b/;

function violationKey(file, line, directive) {
  return `${file}:${line}:TS_SUPPRESSION:${directive}`;
}

function walkTsFiles(dir, callback) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (
      entry.name === "node_modules" ||
      entry.name === "dist" ||
      entry.name === ".encore" ||
      entry.name === "encore.gen" ||
      entry.name === ".git" ||
      entry.name === "tests" ||
      entry.name === "__tests__"
    ) {
      continue;
    }
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkTsFiles(fullPath, callback);
    } else if (
      entry.isFile() &&
      fullPath.endsWith(".ts") &&
      !fullPath.endsWith(".test.ts") &&
      !fullPath.endsWith(".spec.ts") &&
      !fullPath.includes("/tests/") &&
      !fullPath.includes("/__tests__/")
    ) {
      callback(fullPath);
    }
  }
}

export function findTsSuppressions(rootDir) {
  const resolvedRoot = path.resolve(rootDir);
  const targetDirs = [
    path.join(resolvedRoot, "services", "company"),
    path.join(resolvedRoot, "services", "cosa"),
  ];

  const results = [];

  for (const targetDir of targetDirs) {
    walkTsFiles(targetDir, (filePath) => {
      const relFile = path.relative(resolvedRoot, filePath).replace(/\\/g, "/");
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");

      for (let i = 0; i < lines.length; i++) {
        const lineContent = lines[i];
        const match = lineContent.match(DIRECTIVE_REGEX);
        if (match) {
          const directive = `@${match[1]}`;
          results.push({
            file: relFile,
            line: i + 1,
            directive,
          });
        }
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
  } catch {
    return { version: 1, entries: [] };
  }
}

export function writeBaseline(baselinePath, entries) {
  const content = {
    version: 1,
    entries: [...entries].sort(),
  };
  fs.writeFileSync(baselinePath, JSON.stringify(content, null, 2) + "\n", "utf8");
}

export function runCheck({ rootDir = ".", baselinePath = null } = {}) {
  const resolvedRoot = path.resolve(rootDir);
  const suppressions = findTsSuppressions(resolvedRoot);
  const observed = suppressions
    .map(({ file, line, directive }) => violationKey(file, line, directive))
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
  let shouldWriteBaseline = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--root" && args[i + 1]) {
      rootDir = args[++i];
    } else if (args[i] === "--baseline" && args[i + 1]) {
      baselinePath = args[++i];
    } else if (args[i] === "--write-baseline") {
      shouldWriteBaseline = true;
    }
  }

  if (shouldWriteBaseline) {
    if (!baselinePath) {
      console.error("❌ --write-baseline requires --baseline <path>");
      process.exit(1);
    }
    const resolvedRoot = path.resolve(rootDir);
    const suppressions = findTsSuppressions(resolvedRoot);
    const observed = suppressions
      .map(({ file, line, directive }) => violationKey(file, line, directive))
      .sort();
    writeBaseline(baselinePath, observed);
    console.log(`✅ Wrote baseline with ${observed.length} entries to ${baselinePath}`);
    process.exit(0);
  }

  const { observed, additions, stale } = runCheck({ rootDir, baselinePath });

  let failed = false;

  if (additions.length > 0) {
    failed = true;
    console.error("❌ New TypeScript Suppression Violations (@ts-ignore / @ts-expect-error):");
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

  if (observed.length === 0) {
    console.log("✅ TypeScript suppression check passed: ZERO @ts-ignore / @ts-expect-error in codebase.");
  } else {
    console.log(`✅ TypeScript suppression check passed (${observed.length} baseline exceptions allowed).`);
  }
  process.exit(0);
}
