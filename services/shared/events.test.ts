import { describe, expect, it } from "vitest";
import { SCAFFOLD_OK } from "./events";

describe("scaffold", () => {
  it("boots the Encore test runner", () => {
    expect(SCAFFOLD_OK).toBe(true);
  });
});
