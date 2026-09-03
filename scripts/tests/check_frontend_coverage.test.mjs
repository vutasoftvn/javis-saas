import assert from 'node:assert/strict';
import test from 'node:test';

import {
  evaluateCoverage,
  globToRegExp,
  parseCliArgs,
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

// ─── --exclude: bỏ file view/widget khỏi mẫu số line-coverage ───

const lcovWithViews = [
  'SF:lib/modules/x/services/x_service.dart',
  'LF:20',
  'LH:16',
  'end_of_record',
  'SF:lib/modules/x/views/x_view.dart',
  'LF:100',
  'LH:5',
  'end_of_record',
  'SF:lib/modules/x/views/widgets/x_card.dart',
  'LF:80',
  'LH:0',
  'end_of_record',
].join('\n');

test('globToRegExp: ** khớp qua dấu /, * thì không', () => {
  assert.ok(globToRegExp('**/views/**').test('lib/modules/x/views/x_view.dart'));
  assert.ok(!globToRegExp('lib/*/x.dart').test('lib/a/b/x.dart'));
  assert.ok(globToRegExp('lib/*/x.dart').test('lib/a/x.dart'));
});

test('parseLcov áp dụng exclude (chuỗi phân tách bằng dấu phẩy)', () => {
  assert.deepEqual(
    parseLcov(lcovWithViews, { exclude: '**/views/**,**/widgets/**' }),
    { covered: 16, found: 20, percent: 80 },
  );
});

test('parseLcov chấp nhận exclude dạng mảng', () => {
  assert.deepEqual(parseLcov(lcovWithViews, { exclude: ['**/views/**'] }), {
    covered: 16,
    found: 20,
    percent: 80,
  });
});

test('evaluateCoverage: view kéo tụt xuống dưới floor, exclude thì pass', () => {
  assert.throws(() => evaluateCoverage(lcovWithViews, 46), /below required 46%/);
  assert.doesNotThrow(() =>
    evaluateCoverage(lcovWithViews, 46, { exclude: '**/views/**,**/widgets/**' }),
  );
});

test('parseLcov báo lỗi khi exclude loại hết record', () => {
  assert.throws(
    () => parseLcov(lcovWithViews, { exclude: '**' }),
    /no source records after applying --exclude/,
  );
});

test('parseCliArgs: --exclude là tùy chọn, thứ tự bất kỳ', () => {
  assert.deepEqual(
    parseCliArgs(['cov.info', '--minimum=46', '--exclude=**/views/**']),
    { lcovPath: 'cov.info', minimum: 46, exclude: '**/views/**' },
  );
  assert.deepEqual(
    parseCliArgs(['cov.info', '--exclude=**/views/**', '--minimum=46']),
    { lcovPath: 'cov.info', minimum: 46, exclude: '**/views/**' },
  );
  assert.deepEqual(parseCliArgs(['cov.info', '--minimum=46']), {
    lcovPath: 'cov.info',
    minimum: 46,
    exclude: undefined,
  });
});

test('parseCliArgs: thiếu --minimum thì lỗi usage', () => {
  assert.throws(() => parseCliArgs(['cov.info', '--exclude=**/views/**']), /Usage:/);
});
