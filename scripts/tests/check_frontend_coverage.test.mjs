import assert from 'node:assert/strict';
import test from 'node:test';

import {
  evaluateCoverage,
  parseLcov,
} from '../check_frontend_coverage.mjs';

const passingLcov = [
  'SF:lib/a.dart',
  'LF:10',
  'LH:5',
  'end_of_record',
  'SF:lib/b.dart',
  'LF:15',
  'LH:9',
  'end_of_record',
].join('\n');

test('parseLcov aggregates line totals across complete source records', () => {
  assert.deepEqual(parseLcov(passingLcov), {
    covered: 14,
    found: 25,
    percent: 56,
  });
});

test('evaluateCoverage rejects a report below the required floor', () => {
  assert.throws(
    () => evaluateCoverage(passingLcov, 57),
    /below required 57%/,
  );
});

test('parseLcov rejects a source record without covered-line data', () => {
  assert.throws(
    () => parseLcov('SF:lib/a.dart\nLF:10\nend_of_record\n'), /missing LH/);
});

test('parseLcov rejects reports without source records', () => {
  assert.throws(
    () => parseLcov('LF:10\nLH:10\nend_of_record\n'), /missing SF/);
});

test('parseLcov rejects covered lines greater than instrumented lines', () => {
  assert.throws(
    () => parseLcov('SF:lib/a.dart\nLF:10\nLH:11\nend_of_record\n'), /exceeds LF/);
});

test('parseLcov rejects a zero-line report', () => {
  assert.throws(
    () => parseLcov('SF:lib/a.dart\nLF:0\nLH:0\nend_of_record\n'), /positive instrumented line total/);
});
