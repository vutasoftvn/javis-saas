// M0 contract freeze — round-trip cho enum canonical + ID serialization contract.
// Nguồn: shared/contracts/enums.json · Xem M0-contract-freeze.md §Test plan.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import * as enums from "./enums.generated";

const REPO_ROOT = resolve(__dirname, "../../../..");
const src = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "shared/contracts/enums.json"), "utf8"),
);
const idFixtures = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "shared/contracts/fixtures/id-samples.json"), "utf8"),
);

const CASES: Record<string, { arr: readonly string[]; parse: (v: string) => string }> = {
  workspace_lifecycle_stage: {
    arr: enums.WORKSPACE_LIFECYCLE_STAGE,
    parse: enums.parseWorkspaceLifecycleStage,
  },
  project_lifecycle_stage: {
    arr: enums.PROJECT_LIFECYCLE_STAGE,
    parse: enums.parseProjectLifecycleStage,
  },
  workspace_status: { arr: enums.WORKSPACE_STATUS, parse: enums.parseWorkspaceStatus },
  project_status: { arr: enums.PROJECT_STATUS, parse: enums.parseProjectStatus },
  runtime_mode: { arr: enums.RUNTIME_MODE, parse: enums.parseRuntimeMode },
  sync_policy: { arr: enums.SYNC_POLICY, parse: enums.parseSyncPolicy },
  sync_status: { arr: enums.SYNC_STATUS, parse: enums.parseSyncStatus },
  legal_entity_status: {
    arr: enums.LEGAL_ENTITY_STATUS,
    parse: enums.parseLegalEntityStatus,
  },
};

describe("workspace-canonical enums (generated)", () => {
  for (const [name, c] of Object.entries(CASES)) {
    it(`${name}: khớp thứ tự value nguồn`, () => {
      expect([...c.arr]).toEqual(src.enums[name].values);
    });
    it(`${name}: round-trip mọi value`, () => {
      for (const v of src.enums[name].values) expect(c.parse(v)).toBe(v);
    });
    it(`${name}: value lạ -> throw, không map ngầm về default`, () => {
      expect(() => c.parse("__NOT_REAL__")).toThrow(/Unknown/);
    });
  }

  it("stage enum không lẫn mã legacy S*", () => {
    expect(enums.WORKSPACE_LIFECYCLE_STAGE.every((v) => v.startsWith("W"))).toBe(true);
    expect(enums.PROJECT_LIFECYCLE_STAGE.every((v) => v.startsWith("P"))).toBe(true);
  });

  it("migration map phủ đủ target canonical", () => {
    expect(new Set(Object.values(enums.LEGACY_WORKSPACE_STAGE_TO_CANONICAL))).toEqual(
      new Set(enums.WORKSPACE_LIFECYCLE_STAGE),
    );
    expect(new Set(Object.values(enums.LEGACY_PROJECT_STAGE_TO_CANONICAL))).toEqual(
      new Set(enums.PROJECT_LIFECYCLE_STAGE),
    );
  });
});

describe("ID serialization contract (M0)", () => {
  it("Snowflake luôn là decimal string; giá trị 63-bit vỡ nếu dùng Number", () => {
    for (const s of idFixtures.snowflake_decimal_strings.samples) {
      expect(BigInt(s).toString()).toBe(s);
    }
    for (const s of idFixtures.snowflake_decimal_strings
      .must_not_equal_after_double_roundtrip) {
      expect(String(Number(s))).not.toBe(s); // đây là lý do cấm serialize dạng number
      expect(BigInt(s).toString()).toBe(s); // string thì an toàn
    }
  });

  it("JSON.parse giữ Snowflake ở dạng string", () => {
    const decoded = JSON.parse(JSON.stringify({ workspace_id: "9223372036854775807" }));
    expect(typeof decoded.workspace_id).toBe("string");
  });

  it("UUIDv7 fixtures: đúng version 7, variant 10xx, canonical", () => {
    const re =
      /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    for (const s of idFixtures.uuidv7.ordered_samples) expect(s).toMatch(re);
    for (const s of idFixtures.uuidv7.not_v7) expect(s).not.toMatch(re);
  });

  it("UUIDv7 đơn điệu thời gian = sắp xếp lexicographic", () => {
    const o = idFixtures.uuidv7.ordered_samples as string[];
    expect([...o].sort()).toEqual(o);
  });
});
