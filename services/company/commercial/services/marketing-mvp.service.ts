import { and, desc, eq, isNull } from "drizzle-orm";
import { db } from "../db";
import {
  campaignAssets,
  marketingAttributions,
  marketingCampaigns,
  marketingDecisions,
  marketingExperiments,
  marketingLearnings,
  marketingMetricDefinitions,
  marketingMetricObservations,
  marketingObjectives,
  marketingProductMarketing,
  marketingProposals,
  marketingContexts,
} from "../../shared/db/schema/commercial";
import { TenantContext } from "../../shared/types/tenant_context";
import { MvpSourceRef, MvpSuccess, mvpItem, mvpList } from "../../shared/contracts/mvp-response";
import { APIError } from "encore.dev/api";
import type { MarketingContextDTO } from "./marketing-context.service";

const SOURCE_COMPANY_DB: MvpSourceRef = { kind: "company_db", ref: "commercial.marketing" };
const SOURCE_CONNECTOR: MvpSourceRef = { kind: "external_connector", ref: "commercial.marketing_metrics" };

// ─── Marketing Context ───

export async function getMarketingContextMvpService(
  ctx: TenantContext
): Promise<MvpSuccess<MarketingContextDTO>> {
  const { getMarketingContextService } = await import("./marketing-context.service");
  const data = await getMarketingContextService(ctx);
  const isPopulated = !!data.productMarketing.category || data.icpSegments.length > 0 || data.customerResearchThemes.length > 0;
  return {
    data,
    meta: {
      dataState: isPopulated ? "populated" : "empty",
      observedAt: new Date().toISOString(),
      sources: [SOURCE_COMPANY_DB],
    },
  };
}

export async function updateMarketingContextMvpService(
  ctx: TenantContext,
  data: {
    category?: string;
    positioningStatement?: string;
    alternatives?: any[];
    differentiators?: any[];
    brandVoice?: Record<string, any>;
  }
): Promise<MvpSuccess<MarketingContextDTO>> {
  const { updateProductMarketingService } = await import("./marketing-context.service");
  const updated = await updateProductMarketingService(ctx, data);
  return mvpItem(updated, [SOURCE_COMPANY_DB]);
}

// ─── Objectives ───

export interface MarketingObjectiveDTO {
  readonly id: string;
  readonly workspaceId: string;
  readonly title: string;
  readonly description: string | null;
  readonly status: string;
  readonly targetMetric: string | null;
  readonly targetValue: number | null;
  readonly currentValue: number | null;
  readonly startDate: string | null;
  readonly endDate: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export async function listObjectivesService(
  ctx: TenantContext
): Promise<MvpSuccess<readonly MarketingObjectiveDTO[]>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(marketingObjectives)
    .where(and(eq(marketingObjectives.workspaceId, workspaceIdBigInt), isNull(marketingObjectives.deletedAt)))
    .orderBy(desc(marketingObjectives.createdAt));

  const items: MarketingObjectiveDTO[] = rows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    title: r.title,
    description: r.description,
    status: r.status,
    targetMetric: r.targetMetric,
    targetValue: r.targetValue,
    currentValue: r.currentValue,
    startDate: r.startDate?.toISOString() ?? null,
    endDate: r.endDate?.toISOString() ?? null,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_COMPANY_DB]);
}

export async function createObjectiveService(
  ctx: TenantContext,
  data: {
    title: string;
    description?: string;
    targetMetric?: string;
    targetValue?: number;
    startDate?: string;
    endDate?: string;
  }
): Promise<MvpSuccess<MarketingObjectiveDTO>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  const inserted = await db
    .insert(marketingObjectives)
    .values({
      id: BigInt(Date.now()),
      workspaceId: workspaceIdBigInt,
      title: data.title,
      description: data.description || null,
      status: "active",
      targetMetric: data.targetMetric || null,
      targetValue: data.targetValue ?? null,
      currentValue: null,
      startDate: data.startDate ? new Date(data.startDate) : null,
      endDate: data.endDate ? new Date(data.endDate) : null,
    })
    .returning();

  const r = inserted[0];
  return mvpItem(
    {
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      title: r.title,
      description: r.description,
      status: r.status,
      targetMetric: r.targetMetric,
      targetValue: r.targetValue,
      currentValue: r.currentValue,
      startDate: r.startDate?.toISOString() ?? null,
      endDate: r.endDate?.toISOString() ?? null,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    },
    [SOURCE_COMPANY_DB]
  );
}

// ─── Campaigns ───

export interface MarketingCampaignDTO {
  readonly id: string;
  readonly workspaceId: string;
  readonly name: string;
  readonly funnelStage: string;
  readonly channels: unknown;
  readonly budget: number | null;
  readonly status: string;
  readonly startDate: string | null;
  readonly endDate: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export async function listCampaignsMvpService(
  ctx: TenantContext
): Promise<MvpSuccess<readonly MarketingCampaignDTO[]>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(marketingCampaigns)
    .where(and(eq(marketingCampaigns.workspaceId, workspaceIdBigInt), isNull(marketingCampaigns.deletedAt)))
    .orderBy(desc(marketingCampaigns.createdAt));

  const items: MarketingCampaignDTO[] = rows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    name: r.name,
    funnelStage: r.funnelStage,
    channels: r.channels,
    budget: r.budget,
    status: r.status,
    startDate: r.startDate?.toISOString() ?? null,
    endDate: r.endDate?.toISOString() ?? null,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_COMPANY_DB]);
}

export async function createCampaignMvpService(
  ctx: TenantContext,
  data: {
    name: string;
    funnelStage?: string;
    channels?: unknown;
    budget?: number;
    startDate?: string;
    endDate?: string;
  }
): Promise<MvpSuccess<MarketingCampaignDTO>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  const inserted = await db
    .insert(marketingCampaigns)
    .values({
      id: BigInt(Date.now()),
      workspaceId: workspaceIdBigInt,
      name: data.name,
      funnelStage: data.funnelStage || "discover",
      channels: data.channels || null,
      budget: data.budget !== undefined ? data.budget : null,
      status: "draft",
      startDate: data.startDate ? new Date(data.startDate) : null,
      endDate: data.endDate ? new Date(data.endDate) : null,
    })
    .returning();

  const r = inserted[0];
  return mvpItem(
    {
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      name: r.name,
      funnelStage: r.funnelStage,
      channels: r.channels,
      budget: r.budget,
      status: r.status,
      startDate: r.startDate?.toISOString() ?? null,
      endDate: r.endDate?.toISOString() ?? null,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    },
    [SOURCE_COMPANY_DB]
  );
}

// ─── Assets ───

export interface CampaignAssetDTO {
  readonly id: string;
  readonly workspaceId: string;
  readonly campaignId: string;
  readonly assetType: string;
  readonly title: string;
  readonly content: string;
  readonly status: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export async function listAssetsMvpService(
  ctx: TenantContext,
  campaignId?: string
): Promise<MvpSuccess<readonly CampaignAssetDTO[]>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  let whereClause = and(eq(campaignAssets.workspaceId, workspaceIdBigInt), isNull(campaignAssets.deletedAt));
  if (campaignId) {
    whereClause = and(whereClause, eq(campaignAssets.campaignId, BigInt(campaignId)));
  }

  const rows = await db
    .select()
    .from(campaignAssets)
    .where(whereClause)
    .orderBy(desc(campaignAssets.createdAt));

  const items: CampaignAssetDTO[] = rows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    campaignId: r.campaignId.toString(),
    assetType: r.assetType,
    title: r.title,
    content: r.content,
    status: r.status,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_COMPANY_DB]);
}

// ─── Experiments ───

export interface MarketingExperimentDTO {
  readonly id: string;
  readonly workspaceId: string;
  readonly campaignId: string | null;
  readonly name: string;
  readonly hypothesis: string;
  readonly status: string;
  readonly baselineMetric: string | null;
  readonly baselineValue: number | null;
  readonly targetMetric: string | null;
  readonly targetValue: number | null;
  readonly actualValue: number | null;
  readonly conclusion: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export async function listExperimentsMvpService(
  ctx: TenantContext
): Promise<MvpSuccess<readonly MarketingExperimentDTO[]>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(marketingExperiments)
    .where(and(eq(marketingExperiments.workspaceId, workspaceIdBigInt), isNull(marketingExperiments.deletedAt)))
    .orderBy(desc(marketingExperiments.createdAt));

  const items: MarketingExperimentDTO[] = rows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    campaignId: r.campaignId?.toString() ?? null,
    name: r.name,
    hypothesis: r.hypothesis,
    status: r.status,
    baselineMetric: r.baselineMetric,
    baselineValue: r.baselineValue,
    targetMetric: r.targetMetric,
    targetValue: r.targetValue,
    actualValue: r.actualValue,
    conclusion: r.conclusion,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_COMPANY_DB]);
}

export async function createExperimentMvpService(
  ctx: TenantContext,
  data: {
    campaignId?: string;
    name: string;
    hypothesis: string;
    baselineMetric?: string;
    baselineValue?: number;
    targetMetric?: string;
    targetValue?: number;
  }
): Promise<MvpSuccess<MarketingExperimentDTO>> {

  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  if (data.campaignId) {
    const camp = await db
      .select()
      .from(marketingCampaigns)
      .where(and(eq(marketingCampaigns.id, BigInt(data.campaignId)), eq(marketingCampaigns.workspaceId, workspaceIdBigInt)))
      .limit(1);
    if (camp.length === 0) {
      throw APIError.notFound(`Campaign '${data.campaignId}' not found in workspace`);
    }
  }

  const inserted = await db
    .insert(marketingExperiments)
    .values({
      id: BigInt(Date.now()),
      workspaceId: workspaceIdBigInt,
      campaignId: data.campaignId ? BigInt(data.campaignId) : null,
      name: data.name,
      hypothesis: data.hypothesis,
      status: "draft",
      baselineMetric: data.baselineMetric || null,
      baselineValue: data.baselineValue ?? null,
      targetMetric: data.targetMetric || null,
      targetValue: data.targetValue ?? null,
      actualValue: null,
      conclusion: null,
    })
    .returning();

  const r = inserted[0];
  return mvpItem(
    {
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      campaignId: r.campaignId?.toString() ?? null,
      name: r.name,
      hypothesis: r.hypothesis,
      status: r.status,
      baselineMetric: r.baselineMetric,
      baselineValue: r.baselineValue,
      targetMetric: r.targetMetric,
      targetValue: r.targetValue,
      actualValue: r.actualValue,
      conclusion: r.conclusion,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    },
    [SOURCE_COMPANY_DB]
  );
}

// ─── Observed Metrics ───

export interface MarketingObservedMetricDTO {
  readonly id: string;
  readonly workspaceId: string;
  readonly metricName: string;
  readonly unit: string;
  readonly providerKey: string;
  readonly sourceRecordId: string;
  readonly observedAt: string;
  readonly ingestedAt: string;
  readonly value: number;
  readonly metadata: unknown;
}

export async function getObservedMetricsMvpService(
  ctx: TenantContext,
  providerKey?: string
): Promise<MvpSuccess<readonly MarketingObservedMetricDTO[]>> {
  const workspaceIdBigInt = BigInt(ctx.workspaceId);

  const whereClause = providerKey
    ? and(
        eq(marketingMetricObservations.workspaceId, workspaceIdBigInt),
        eq(marketingMetricObservations.providerKey, providerKey)
      )!
    : eq(marketingMetricObservations.workspaceId, workspaceIdBigInt);

  const rows = await db
    .select({
      obs: marketingMetricObservations,
      def: marketingMetricDefinitions,
    })
    .from(marketingMetricObservations)
    .innerJoin(marketingMetricDefinitions, eq(marketingMetricObservations.metricId, marketingMetricDefinitions.id))
    .where(whereClause)
    .orderBy(desc(marketingMetricObservations.observedAt))
    .limit(100);

  const items: MarketingObservedMetricDTO[] = rows.map(({ obs, def }) => ({
    id: obs.id.toString(),
    workspaceId: obs.workspaceId.toString(),
    metricName: def.name,
    unit: def.unit,
    providerKey: obs.providerKey,
    sourceRecordId: obs.sourceRecordId,
    observedAt: obs.observedAt.toISOString(),
    ingestedAt: obs.ingestedAt.toISOString(),
    value: obs.value,
    metadata: obs.metadata,
  }));

  return mvpList(items, [SOURCE_CONNECTOR]);
}
