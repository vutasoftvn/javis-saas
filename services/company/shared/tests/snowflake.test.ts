import { describe, it, expect } from "vitest";
import { generateSnowflake, generateSnowflakeStr } from "../services/snowflake.service";

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
});
