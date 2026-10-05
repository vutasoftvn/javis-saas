import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseDoneCriteria } from "../services/done-criteria";

interface Fixtures {
  valid: { name: string; input: unknown; normalized: unknown }[];
  invalid: { name: string; input: unknown; error: string }[];
}
const here = fileURLToPath(new URL(".", import.meta.url));
const fixtures: Fixtures = JSON.parse(
  readFileSync(resolve(here, "../../../../shared/contracts/done-criteria.fixtures.json"), "utf8"),
);

describe("parseDoneCriteria (shared fixtures)", () => {
  for (const c of fixtures.valid) {
    it(`accepts and normalizes: ${c.name}`, () => {
      expect(parseDoneCriteria(c.input)).toEqual(c.normalized);
    });
  }
  for (const c of fixtures.invalid) {
    it(`rejects: ${c.name}`, () => {
      expect(() => parseDoneCriteria(c.input)).toThrow(c.error);
    });
  }
});
