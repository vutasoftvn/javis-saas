import { describe, expect, it } from "vitest";
import { assessApplicableObligations } from "../services/legal-applicability.service";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  regulationSources,
  regulationVersions,
  legalObligationTemplates,
  applicabilityRules,
} = schema;

describe("legal-applicability service", () => {
  it("evaluates applicable obligations matching active regulation rules", async () => {
    const wsId = generateSnowflake();
    await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });

    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Enterprise Law",
      issuer: "National Assembly",
      number: `LAW-${Date.now()}`,
      url: "https://example.gov.vn/law",
      layer: "CURRENT_LAW",
    });

    const verId = generateSnowflake();
    await db.insert(regulationVersions).values({
      id: verId,
      regulationSourceId: sourceId,
      version: "2026",
      effectiveFrom: "2026-01-01" as any,
    });

    const tplId = generateSnowflake();
    await db.insert(legalObligationTemplates).values({
      id: tplId,
      regulationVersionId: verId,
      title: "File annual registration update",
      typicalDueOffsetDays: 30,
    });

    const ruleId = generateSnowflake();
    await db.insert(applicabilityRules).values({
      id: ruleId,
      regulationVersionId: verId,
      obligationTemplateId: tplId,
      predicate: { entity_status: "DRAFT" },
    });

    const obligations = await assessApplicableObligations(wsId);
    const matched = obligations.find((o) => o.obligationTemplateId === String(tplId));
    expect(matched).toBeDefined();
    expect(matched?.title).toBe("File annual registration update");
    expect(matched?.sourceRegulationNumber).toContain("LAW-");
    expect(matched?.hasExistingInstance).toBe(false);
  });
});
