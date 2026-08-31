#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);

function parseLineCount(value, label) {
  if (!/^\d+$/.test(value)) {
    throw new Error(`LCOV ${label} must be a non-negative integer`);
  }
  return Number(value);
}

function finishRecord(record, records) {
  if (record.source === undefined && record.lf === undefined && record.lh === undefined) {
    return;
  }
  if (!record.source) {
    throw new Error('LCOV record missing SF');
  }
  if (record.lf === undefined) {
    throw new Error(`LCOV record for ${record.source} missing LF`);
  }
  if (record.lh === undefined) {
    throw new Error(`LCOV record for ${record.source} missing LH`);
  }
  if (record.lh > record.lf) {
    throw new Error(`LCOV record for ${record.source} has LH ${record.lh} exceeds LF ${record.lf}`);
  }
  records.push(record);
}

export function parseLcov(lcov) {
  if (typeof lcov !== 'string') {
    throw new TypeError('LCOV input must be a string');
  }

  const records = [];
  let record = {};

  for (const rawLine of lcov.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line === 'end_of_record') {
      finishRecord(record, records);
      record = {};
      continue;
    }
    if (line.startsWith('SF:')) {
      if (record.source !== undefined) {
        throw new Error(`LCOV record for ${record.source} is missing end_of_record`);
      }
      const source = line.slice(3);
      if (!source) {
        throw new Error('LCOV record missing SF');
      }
      record.source = source;
      continue;
    }
    if (line.startsWith('LF:')) {
      if (record.lf !== undefined) {
        throw new Error(`LCOV record${record.source ? ` for ${record.source}` : ''} has duplicate LF`);
      }
      record.lf = parseLineCount(line.slice(3), 'LF');
      continue;
    }
    if (line.startsWith('LH:')) {
      if (record.lh !== undefined) {
        throw new Error(`LCOV record${record.source ? ` for ${record.source}` : ''} has duplicate LH`);
      }
      record.lh = parseLineCount(line.slice(3), 'LH');
    }
  }

  finishRecord(record, records);
  if (records.length === 0) {
    throw new Error('LCOV report contains no source records');
  }

  const covered = records.reduce((total, current) => total + current.lh, 0);
  const found = records.reduce((total, current) => total + current.lf, 0);
  if (found === 0) {
    throw new Error('LCOV report must contain a positive instrumented line total');
  }

  return {
    covered,
    found,
    percent: Number(((covered / found) * 100).toFixed(2)),
  };
}

export function evaluateCoverage(lcov, minimum) {
  if (!Number.isFinite(minimum) || minimum < 0) {
    throw new Error('Coverage minimum must be a non-negative number');
  }

  const summary = parseLcov(lcov);
  if (summary.covered * 100 < summary.found * minimum) {
    throw new Error(
      `Frontend line coverage ${summary.percent.toFixed(2)}% is below required ${minimum}%`,
    );
  }
  return summary;
}

function parseCliArgs(args) {
  const [lcovPath, ...options] = args;
  if (!lcovPath || options.length !== 1 || !options[0].startsWith('--minimum=')) {
    throw new Error('Usage: node scripts/check_frontend_coverage.mjs <lcov-path> --minimum=<non-negative-number>');
  }

  const minimum = Number(options[0].slice('--minimum='.length));
  if (!Number.isFinite(minimum) || minimum < 0) {
    throw new Error('Coverage minimum must be a non-negative number');
  }
  return { lcovPath, minimum };
}

function main() {
  try {
    const { lcovPath, minimum } = parseCliArgs(process.argv.slice(2));
    const lcov = fs.readFileSync(path.resolve(process.cwd(), lcovPath), 'utf8');
    const { covered, found, percent } = evaluateCoverage(lcov, minimum);
    console.log(`Frontend line coverage: ${percent.toFixed(2)}% (${covered}/${found})`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

if (process.argv[1] === __filename) {
  main();
}
