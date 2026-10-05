import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { mapOkrDbError, withOkrDbErrors } from "../services/okr-db-errors";

describe("mapOkrDbError", () => {
  it("maps a 23514 error to failedPrecondition with the db message", () => {
    const mapped = mapOkrDbError({ code: "23514", message: "x" });
    expect(mapped).toBeInstanceOf(APIError);
    expect(mapped).toMatchObject({ code: "failed_precondition", message: "x" });
  });

  it("maps a nested cause 23514", () => {
    const mapped = mapOkrDbError({ message: "Failed query", cause: { code: "23514", message: "trigger said no" } });
    expect(mapped).toMatchObject({ code: "failed_precondition", message: "trigger said no" });
  });

  it("passes other errors through unchanged", () => {
    const err = { code: "23505", message: "dup" };
    expect(mapOkrDbError(err)).toBe(err);
    const plain = new Error("boom");
    expect(mapOkrDbError(plain)).toBe(plain);
  });

  it("withOkrDbErrors rethrows the mapped error", async () => {
    await expect(withOkrDbErrors(() => Promise.reject({ code: "23514", message: "m" }))).rejects.toMatchObject({
      code: "failed_precondition",
    });
  });
});
