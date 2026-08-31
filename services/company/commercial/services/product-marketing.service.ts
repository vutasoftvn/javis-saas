import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  assembleContextDTO,
  getOrCreateContextRow,
  MarketingContextDTO,
  recordRevisionSnapshot,
  verifyOptimisticLock,
} from "./marketing-snapshot.service";

const { marketingContexts, marketingProductMarketing } = schema;

export interface ProductMarketingDTO {
  category: string | null;
  positioningStatement: string | null;
  alternatives: any[];
  differentiators: any[];
  brandVoice: Record<string, any>;
}

export interface UpdateProductMarketingParams {
  category?: string;
  positioningStatement?: string;
  alternatives?: any[];
  differentiators?: any[];
  brandVoice?: Record<string, any>;
  expectedRevision?: number;
  sourceSkillId?: string;
  sourceSkillVersion?: string;
  sourceSkillHash?: string;
}

export async function updateProductMarketingService(
  ctx: TenantContext,
  params: UpdateProductMarketingParams
): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  // Update or insert product marketing
  const [existingPm] = await db
    .select({ id: marketingProductMarketing.id })
    .from(marketingProductMarketing)
    .where(
      and(
        eq(marketingProductMarketing.workspaceId, wsId),
        eq(marketingProductMarketing.contextId, contextRow.id)
      )
    )
    .limit(1);

  if (existingPm) {
    await db
      .update(marketingProductMarketing)
      .set({
        category: params.category !== undefined ? params.category : undefined,
        positioningStatement: params.positioningStatement !== undefined ? params.positioningStatement : undefined,
        alternatives: params.alternatives !== undefined ? params.alternatives : undefined,
        differentiators: params.differentiators !== undefined ? params.differentiators : undefined,
        brandVoice: params.brandVoice !== undefined ? params.brandVoice : undefined,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(marketingProductMarketing.workspaceId, wsId),
          eq(marketingProductMarketing.contextId, contextRow.id)
        )
      );
  } else {
    await db.insert(marketingProductMarketing).values({
      id: generateSnowflake(),
      contextId: contextRow.id,
      workspaceId: wsId,
      category: params.category ?? null,
      positioningStatement: params.positioningStatement ?? null,
      alternatives: params.alternatives ?? [],
      differentiators: params.differentiators ?? [],
      brandVoice: params.brandVoice ?? {},
    });
  }

  // Update context root revision & provenance
  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      revision: nextRevision,
      status: "draft",
      updatedByUserId: userId,
      sourceSkillId: params.sourceSkillId !== undefined ? params.sourceSkillId : contextRow.sourceSkillId,
      sourceSkillVersion: params.sourceSkillVersion !== undefined ? params.sourceSkillVersion : contextRow.sourceSkillVersion,
      sourceSkillHash: params.sourceSkillHash !== undefined ? params.sourceSkillHash : contextRow.sourceSkillHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId,
    {
      id: params.sourceSkillId,
      version: params.sourceSkillVersion,
      hash: params.sourceSkillHash,
    }
  );

  return dto;
}
