import { describe, expect, it } from "vitest";
import {
  getVentureProfileService,
  upsertVentureProfileService,
} from "../strategy/services/venture-profile.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("venture-profile service", () => {
  it("creates and retrieves venture profile", async () => {
    const wsId = generateSnowflake();

    const created = await upsertVentureProfileService({
      workspaceId: wsId,
      problemStatement: "Solving automated accounting for solo founders",
      targetCustomer: "Solo founders in Vietnam",
      industry: "Fintech SaaS",
      geography: "Vietnam",
      currency: "VND",
      initialRunwayMonths: 12,
    });

    expect(created.workspaceId).toBe(String(wsId));
    expect(created.industry).toBe("Fintech SaaS");
    expect(created.currency).toBe("VND");

    const fetched = await getVentureProfileService(wsId);
    expect(fetched).not.toBeNull();
    expect(fetched?.problemStatement).toBe("Solving automated accounting for solo founders");
  });

  it("updates existing venture profile idempotently", async () => {
    const wsId = generateSnowflake();

    await upsertVentureProfileService({
      workspaceId: wsId,
      industry: "Ecommerce",
      initialRunwayMonths: 6,
    });

    const updated = await upsertVentureProfileService({
      workspaceId: wsId,
      industry: "B2B SaaS",
      initialRunwayMonths: 18,
    });

    expect(updated.industry).toBe("B2B SaaS");
    expect(updated.initialRunwayMonths).toBe(18);
  });
});
