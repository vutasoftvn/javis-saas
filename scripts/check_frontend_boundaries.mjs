#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const defaultFrontendLibDir = path.join(rootDir, 'frontend', 'lib');

let violations = [];

function recordViolation(baseDir, filePath, lineNum, rule, explanation) {
  const relPath = path.relative(baseDir, filePath).replace(/\\/g, '/');
  violations.push(`${relPath}:${lineNum}:${rule}:${explanation}`);
}

function walkDir(dir, callback) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkDir(fullPath, callback);
    } else if (entry.isFile() && fullPath.endsWith('.dart')) {
      callback(fullPath);
    }
  }
}

function checkFile(baseDir, filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  const relFromLib = path.relative(baseDir, filePath).replace(/\\/g, '/');

  // Determine if file is in features/
  let currentFeature = null;
  const featureMatch = relFromLib.match(/^features\/([^/]+)\//);
  if (featureMatch) {
    currentFeature = featureMatch[1];
  }

  const isHologram = relFromLib.includes('hologram');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Match import statements
    const importMatch = line.match(/^\s*import\s+['"]([^'"]+)['"]/);
    if (!importMatch) continue;

    const rawImport = importMatch[1];

    // Rule 1: No importing WorkspaceScopedService from new features or migrated modules
    if (currentFeature != null) {
      if (rawImport.includes('workspace_scoped_service.dart')) {
        recordViolation(
          baseDir,
          filePath,
          lineNum,
          'NO_LEGACY_WORKSPACE_SCOPED_SERVICE',
          'Features must use MvpRequestClient/MvpEndpoint directly rather than legacy WorkspaceScopedService'
        );
      }
    }

    // Resolve normalized target path for package:frontend/ or relative imports
    let targetRelFromLib = null;
    if (rawImport.startsWith('package:frontend/')) {
      targetRelFromLib = rawImport.replace('package:frontend/', '');
    } else if (rawImport.startsWith('.')) {
      const fileDir = path.dirname(filePath);
      const resolved = path.resolve(fileDir, rawImport);
      if (resolved.startsWith(baseDir)) {
        targetRelFromLib = path.relative(baseDir, resolved).replace(/\\/g, '/');
      }
    }

    if (!targetRelFromLib) continue;

    // Check target feature imports
    const targetFeatureMatch = targetRelFromLib.match(/^features\/([^/]+)\/(.*)$/);
    if (targetFeatureMatch) {
      const targetFeature = targetFeatureMatch[1];
      const targetSubPath = targetFeatureMatch[2];

      // If another feature or module or hub is importing this feature, it MUST import public.dart (or _shared)
      if (targetFeature !== '_shared' && targetFeature !== currentFeature) {
        if (targetSubPath !== 'public.dart') {
          recordViolation(
            baseDir,
            filePath,
            lineNum,
            'CROSS_FEATURE_PRIVATE_IMPORT',
            `Cannot import internal "${targetSubPath}" from feature "${targetFeature}". Import "public.dart" facade only.`
          );
        }
      }
    }

    // Rule: Hologram Hub cannot import internal implementations of features
    if (isHologram && targetFeatureMatch) {
      const targetFeature = targetFeatureMatch[1];
      const targetSubPath = targetFeatureMatch[2];
      if (targetFeature !== '_shared' && targetFeature !== currentFeature) {
        if (targetSubPath !== 'public.dart') {
          recordViolation(
            baseDir,
            filePath,
            lineNum,
            'HOLOGRAM_CROSS_FEATURE_IMPORT',
            `Hologram cannot import internal "${targetSubPath}" from feature "${targetFeature}". Import "public.dart" facade only.`
          );
        }
      }
    }
  }
}

export function runCheck(targetDir = defaultFrontendLibDir) {
  violations = [];
  walkDir(targetDir, (fp) => checkFile(targetDir, fp));
  return violations;
}

// CLI entry point
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const customTarget = process.argv[2] ? path.resolve(process.argv[2]) : defaultFrontendLibDir;
  const issues = runCheck(customTarget);
  if (issues.length > 0) {
    console.error('Frontend Boundary Violations:');
    for (const v of issues) {
      console.error(`  ${v}`);
    }
    process.exit(1);
  } else {
    console.log('✅ Frontend boundaries check passed.');
  }
}
