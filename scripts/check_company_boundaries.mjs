#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const defaultCompanyDir = path.join(rootDir, 'services', 'company');

let violations = [];

function recordViolation(baseDir, filePath, lineNum, rule, explanation) {
  const relPath = path.relative(baseDir, filePath).replace(/\\/g, '/');
  violations.push(`${relPath}:${lineNum}:${rule}:${explanation}`);
}

function walkDir(dir, callback) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name === '.encore') continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkDir(fullPath, callback);
    } else if (entry.isFile() && fullPath.endsWith('.ts') && !fullPath.endsWith('.d.ts') && !fullPath.includes('/tests/') && !fullPath.includes('.test.ts')) {
      callback(fullPath);
    }
  }
}

function checkFile(baseDir, filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  const rel = path.relative(baseDir, filePath).replace(/\\/g, '/');

  const isDomain = rel.includes('/domain/');
  const isApplication = rel.includes('/application/');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Match import statements: import ... from '...'; or import '...';
    const importMatch = line.match(/^\s*import\s+(?:.*from\s+)?['"]([^'"]+)['"]/);
    if (!importMatch) continue;

    const rawImport = importMatch[1];

    if (isDomain) {
      if (rawImport.startsWith('encore.dev')) {
        recordViolation(
          baseDir,
          filePath,
          lineNum,
          'DOMAIN_ENCORE_IMPORT',
          `Domain module cannot import Encore package "${rawImport}"`
        );
      }
      if (rawImport.startsWith('drizzle-orm') || rawImport.includes('schema') || rawImport.includes('db')) {
        recordViolation(
          baseDir,
          filePath,
          lineNum,
          'DOMAIN_DB_IMPORT',
          `Domain module cannot import database/Drizzle package "${rawImport}"`
        );
      }
      if (rawImport.includes('/handlers/') || rawImport.includes('/infrastructure/') || rawImport.includes('/services/')) {
        recordViolation(
          baseDir,
          filePath,
          lineNum,
          'DOMAIN_LAYER_INVERSION',
          `Domain module cannot import outer layer "${rawImport}"`
        );
      }
      if (rawImport.includes('packages/agent') || rawImport.includes('agent.')) {
        recordViolation(
          baseDir,
          filePath,
          lineNum,
          'DOMAIN_AGENT_IMPORT',
          `Company domain module cannot import Agent plane code "${rawImport}"`
        );
      }
    }

    if (isApplication) {
      if (rawImport.includes('/handlers/')) {
        recordViolation(
          baseDir,
          filePath,
          lineNum,
          'APPLICATION_HANDLER_IMPORT',
          `Application use-case cannot import HTTP handler "${rawImport}"`
        );
      }
    }
  }
}

export function runCheck(targetDir = defaultCompanyDir) {
  violations = [];
  walkDir(targetDir, (fp) => checkFile(targetDir, fp));
  return violations;
}

// CLI entry point
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const customTarget = process.argv[2] ? path.resolve(process.argv[2]) : defaultCompanyDir;
  const issues = runCheck(customTarget);
  if (issues.length > 0) {
    console.error('Company Boundary Violations:');
    for (const v of issues) {
      console.error(`  ${v}`);
    }
    process.exit(1);
  } else {
    console.log('✅ Company boundaries check passed.');
  }
}
