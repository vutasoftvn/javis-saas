import test from "node:test";
import assert from "node:assert/strict";
import { normalizeCheckClause as n } from "../../scripts/schema-fingerprint-lib.mjs";

const pairs = [
  ["((delivery_attempts >= 0))", "(delivery_attempts >= 0)"],
  ["(((size_bytes IS NULL) OR (size_bytes >= 0)))", "((size_bytes IS NULL) OR (size_bytes >= 0))"],
  ["((a > 0))", "(a > 0)"],
  ["(((x = 1) AND (y = 2)))", "((x = 1) AND (y = 2))"],
];

test("PG16 and PG18 forms normalize equal", () => {
  for (const [a, b] of pairs) assert.equal(n(a), n(b));
  assert.equal(n("(delivery_attempts >= 0)"), "(delivery_attempts >= 0)");
});

test("top-level conjunction without outer pair is preserved and wrapped", () => {
  assert.equal(n("(a) AND (b)"), "((a) AND (b))");
  assert.equal(n("((a) AND (b))"), "((a) AND (b))");
  assert.equal(n("(((a) AND (b)))"), "((a) AND (b))");
});

test("parens and quotes inside string literals are ignored", () => {
  assert.equal(n("((x = ')'::text))"), "(x = ')'::text)");
  assert.equal(n("(x = ')'::text)"), "(x = ')'::text)");
  assert.equal(n("((x = '('::text)) AND (y)"), "(((x = '('::text)) AND (y))");
  assert.equal(n("((x = 'it''s)'::text))"), "(x = 'it''s)'::text)");
});

test("empty and whitespace", () => {
  assert.equal(n(""), null);
  assert.equal(n("   "), null);
  assert.equal(n(null), null);
  assert.equal(n(undefined), null);
  assert.equal(n("  ((  a   >  0  ))  "), "(a > 0)");
});
