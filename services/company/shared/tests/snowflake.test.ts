import { afterEach, describe, it, expect } from "vitest";
import {
  generateSnowflake,
  generateSnowflakeStr,
  decodeSnowflake,
  __resetSnowflakeForTest,
  COSA_SNOWFLAKE_EPOCH_MS,
} from "../services/snowflake.service";

afterEach(() => {
  delete process.env.COMPANY_SNOWFLAKE_SLOT;
  __resetSnowflakeForTest();
});

describe("Snowflake ID Generator & String Contract", () => {
  it("generates 64-bit snowflake IDs strictly larger than Number.MAX_SAFE_INTEGER", () => {
    const id = generateSnowflake();
    const maxSafe = BigInt(Number.MAX_SAFE_INTEGER);

    expect(id > maxSafe).toBe(true);
  });

  it("ensures string round-trip preserves precision where Number() loses precision", () => {
    const id = generateSnowflake();
    const str = id.toString();
    const parsedBigInt = BigInt(str);

    expect(parsedBigInt).toBe(id);
    expect(str).toBe(parsedBigInt.toString());

    // Verify generateSnowflakeStr() returns string representation
    const strGenerated = generateSnowflakeStr();
    expect(typeof strGenerated).toBe("string");
    expect(BigInt(strGenerated) > BigInt(Number.MAX_SAFE_INTEGER)).toBe(true);
  });

  it("generates distinct sequential identifiers", () => {
    const set = new Set<string>();
    for (let i = 0; i < 100; i++) {
      set.add(generateSnowflakeStr());
    }
    expect(set.size).toBe(100);
  });

  // M2 §2 — bit layout v1 + slot từ env (không random node ID).
  it("encodes the configured slot from COMPANY_SNOWFLAKE_SLOT + a decodable timestamp", () => {
    process.env.COMPANY_SNOWFLAKE_SLOT = "37";
    __resetSnowflakeForTest();
    const d = decodeSnowflake(generateSnowflake());
    expect(d.slot).toBe(37);
    expect(d.timestampMs).toBeGreaterThan(COSA_SNOWFLAKE_EPOCH_MS);
  });

  it("rejects an out-of-range slot", () => {
    process.env.COMPANY_SNOWFLAKE_SLOT = "9999";
    __resetSnowflakeForTest();
    expect(() => generateSnowflake()).toThrow(/COMPANY_SNOWFLAKE_SLOT/);
  });

  it("is strictly monotonic across many rapid calls (no random sequence start)", () => {
    __resetSnowflakeForTest();
    let prev = generateSnowflake();
    for (let i = 0; i < 10000; i++) {
      const next = generateSnowflake();
      expect(next).toBeGreaterThan(prev);
      prev = next;
    }
  });
});
