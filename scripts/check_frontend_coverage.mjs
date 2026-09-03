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

/**
 * Chuyển một glob đơn giản (`*`, `**`, `?`) sang RegExp khớp toàn bộ chuỗi.
 * `**` khớp mọi ký tự kể cả `/`; `*` khớp mọi ký tự trừ `/`.
 */
export function globToRegExp(glob) {
  let re = '';
  for (let i = 0; i < glob.length; i += 1) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') {
        re += '.*';
        i += 1;
      } else {
        re += '[^/]*';
      }
    } else if (c === '?') {
      re += '[^/]';
    } else if ('\\^$.|+()[]{}'.includes(c)) {
      re += `\\${c}`;
    } else {
      re += c;
    }
  }
  return new RegExp(`^${re}$`);
}

function normalizeExclude(exclude) {
  if (exclude === undefined || exclude === null) {
    return [];
  }
  const patterns = Array.isArray(exclude) ? exclude : String(exclude).split(',');
  return patterns
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
    .map((p) => globToRegExp(p));
}

export function parseLcov(lcov, { exclude } = {}) {
  if (typeof lcov !== 'string') {
    throw new TypeError('LCOV input must be a string');
  }

  const excludeRes = normalizeExclude(exclude);
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

  const included = records.filter(
    (current) => !excludeRes.some((re) => re.test(current.source)),
  );
  if (included.length === 0) {
    throw new Error('LCOV report contains no source records after applying --exclude');
  }

  const covered = included.reduce((total, current) => total + current.lh, 0);
  const found = included.reduce((total, current) => total + current.lf, 0);
  if (found === 0) {
    throw new Error('LCOV report must contain a positive instrumented line total');
  }

  return {
    covered,
    found,
    percent: Number(((covered / found) * 100).toFixed(2)),
  };
}

export function evaluateCoverage(lcov, minimum, { exclude } = {}) {
  if (!Number.isFinite(minimum) || minimum < 0) {
    throw new Error('Coverage minimum must be a non-negative number');
  }

  const summary = parseLcov(lcov, { exclude });
  if (summary.covered * 100 < summary.found * minimum) {
    throw new Error(
      `Frontend line coverage ${summary.percent.toFixed(2)}% is below required ${minimum}%`,
    );
  }
  return summary;
}

export function parseCliArgs(args) {
  const usage =
    'Usage: node scripts/check_frontend_coverage.mjs <lcov-path> --minimum=<non-negative-number> [--exclude=<glob>[,<glob>...]]';
  const [lcovPath, ...options] = args;
  if (!lcovPath || options.length < 1 || options.length > 2) {
    throw new Error(usage);
  }

  let minimumRaw;
  let exclude;
  for (const opt of options) {
    if (opt.startsWith('--minimum=')) {
      minimumRaw = opt.slice('--minimum='.length);
    } else if (opt.startsWith('--exclude=')) {
      exclude = opt.slice('--exclude='.length);
    } else {
      throw new Error(usage);
    }
  }
  if (minimumRaw === undefined) {
    throw new Error(usage);
  }

  const minimum = Number(minimumRaw);
  if (!Number.isFinite(minimum) || minimum < 0) {
    throw new Error('Coverage minimum must be a non-negative number');
  }
  return { lcovPath, minimum, exclude };
}

function main() {
  try {
    const { lcovPath, minimum, exclude } = parseCliArgs(process.argv.slice(2));
    const lcov = fs.readFileSync(path.resolve(process.cwd(), lcovPath), 'utf8');
    const { covered, found, percent } = evaluateCoverage(lcov, minimum, { exclude });
    console.log(`Frontend line coverage: ${percent.toFixed(2)}% (${covered}/${found})`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

if (process.argv[1] === __filename) {
  main();
}
