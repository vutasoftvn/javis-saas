import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";
import {
  assessApplicableObligations,
  evaluateEntityApplicability,
} from "../services/legal-applicability.service";
import {
  listOpenObligations,
  createObligationInstanceService,
} from "../services/legal-obligation.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  evaluateLegalPredicate,
  evaluateLegalPredicateWithDetails,
} from "../services/legal-predicate";

const {
  regulationSources,
  regulationVersions,
  legalObligationTemplates,
  applicabilityRules,
  legalEntityProfiles,
  applicabilityEvaluations,
  legalObligationInstances,
} = schema;

describe("legal-applicability-integrity", () => {
  it("evaluates applicability per legal entity and avoids single-entity assumptions", async () => {
    const wsId = generateSnowflake();

    // Create Entity A (VERIFIED)
    const entityAId = generateSnowflake();
    await db.insert(legalEntityProfiles).values({
      id: entityAId,
      workspaceId: wsId,
      legalName: "Entity A Corp",
      entityType: "MICRO_ENTERPRISE",
      status: "VERIFIED",
    });

    // Create Entity B (DRAFT)
    const entityBId = generateSnowflake();
    await db.insert(legalEntityProfiles).values({
      id: entityBId,
      workspaceId: wsId,
      legalName: "Entity B Co",
      entityType: "MICRO_ENTERPRISE",
      status: "DRAFT",
    });

    // Create Regulation Source & Version
    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Verified Entity Obligation Law",
      issuer: "Ministry of Finance",
      number: `LAW-ENT-${Date.now()}`,
      url: "https://example.gov.vn/law-ent",
      layer: "CURRENT_LAW",
    });

    const verId = generateSnowflake();
    await db.insert(regulationVersions).values({
      id: verId,
      regulationSourceId: sourceId,
      version: "2026.1",
      effectiveFrom: "2026-01-01" as any,
    });

    const tplId = generateSnowflake();
    await db.insert(legalObligationTemplates).values({
      id: tplId,
      regulationVersionId: verId,
      title: "Mandatory Verified Entity Disclosure",
      typicalDueOffsetDays: 15,
    });

    // Rule: applies only to VERIFIED entities
    const ruleId = generateSnowflake();
    await db.insert(applicabilityRules).values({
      id: ruleId,
      regulationVersionId: verId,
      obligationTemplateId: tplId,
      predicate: { entity_status: "VERIFIED" },
    });

    // Evaluate Entity A directly
    const evalA = await evaluateEntityApplicability(
      { workspaceId: wsId },
      String(entityAId)
    );
    const ruleEvalA = evalA.find((e) => e.ruleId === String(ruleId));
    expect(ruleEvalA).toBeDefined();
    expect(ruleEvalA?.evaluationResult).toBe("APPLIES");

    // Evaluate Entity B directly - does not match predicate, so omitted from applicable obligations
    const evalB = await evaluateEntityApplicability(
      { workspaceId: wsId },
      String(entityBId)
    );
    const ruleEvalB = evalB.find((e) => e.ruleId === String(ruleId));
    expect(ruleEvalB).toBeUndefined();

    // Verify persisted evaluations in legal.applicability_evaluations
    const persisted = await db.select().from(applicabilityEvaluations);
    const matchA = persisted.find(
      (p) => p.legalEntityId === entityAId && p.ruleId === ruleId
    );
    expect(matchA?.result).toBe("APPLIES");

    const matchB = persisted.find(
      (p) => p.legalEntityId === entityBId && p.ruleId === ruleId
    );
    expect(matchB?.result).toBe("NOT_APPLIES");

    // assessApplicableObligations aggregates across entities and includes Entity A
    const applicable = await assessApplicableObligations(wsId);
    const matched = applicable.find((o) => o.obligationTemplateId === String(tplId));
    expect(matched).toBeDefined();
    expect(matched?.title).toBe("Mandatory Verified Entity Disclosure");
    expect(matched?.legalEntityId).toBe(String(entityAId));
  });

  it("handles predicates robustly: unknown fields and missing facts return NEEDS_REVIEW", () => {
    // Unknown field in predicate -> NEEDS_REVIEW
    const unknownRes = evaluateLegalPredicateWithDetails(
      { unknown_field_xyz: "value" },
      { entityStatus: "VERIFIED", accountingRegime: "TT133", fiscalYearStart: null }
    );
    expect(unknownRes.result).toBe("NEEDS_REVIEW");
    expect(unknownRes.reasonCodes.some((c) => c.includes("unknown_predicate_field"))).toBe(true);

    // Missing accounting regime when required by predicate -> NEEDS_REVIEW
    const missingRes = evaluateLegalPredicateWithDetails(
      { accounting_regime: "TT133" },
      { entityStatus: "VERIFIED", accountingRegime: null, fiscalYearStart: null }
    );
    expect(missingRes.result).toBe("NEEDS_REVIEW");
    expect(missingRes.reasonCodes.some((c) => c.includes("missing_fact:accountingRegime"))).toBe(true);

    // Mismatched regime -> NOT_APPLIES
    const mismatchRes = evaluateLegalPredicate(
      { accounting_regime: "TT133" },
      { entityStatus: "VERIFIED", accountingRegime: "TT200", fiscalYearStart: null }
    );
    expect(mismatchRes).toBe("NOT_APPLIES");

    // Matching regime -> APPLIES
    const matchRes = evaluateLegalPredicate(
      { accounting_regime: "TT133", entity_status: "VERIFIED" },
      { entityStatus: "VERIFIED", accountingRegime: "TT133", fiscalYearStart: null }
    );
    expect(matchRes).toBe("APPLIES");
  });

  it("retrieves open obligations and filters out fulfilled/cancelled ones", async () => {
    const wsId = generateSnowflake();

    // Create open obligation
    const ob1 = await createObligationInstanceService({
      workspaceId: wsId,
      source: "USER_CREATED",
      title: "Open Tax Filing",
      dueDate: "2026-01-01", // in past, overdue
    });
    expect(ob1.status).toBe("OPEN");

    // Create fulfilled obligation
    const ob2 = await createObligationInstanceService({
      workspaceId: wsId,
      source: "USER_CREATED",
      title: "Completed Regulatory Audit",
      dueDate: "2026-12-31",
    });
    await db
      .update(legalObligationInstances)
      .set({ status: "FULFILLED" })
      .where(eq(legalObligationInstances.id, BigInt(ob2.id)));

    // Query open obligations
    const openList = await listOpenObligations({ workspaceId: wsId });
    const titles = openList.map((o) => o.title);

    expect(titles).toContain("Open Tax Filing");
    expect(titles).not.toContain("Completed Regulatory Audit");

    const overdueOb = openList.find((o) => o.id === ob1.id);
    expect(overdueOb?.isOverdue).toBe(true);
    expect(overdueOb?.overdueDays).toBeGreaterThan(0);
  });
});
