import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

const { interviews } = schema;

export interface Interview {
  id: string;
  companyId: string;
  workspaceId: string;
  projectId: string;
  contactRef: string | null;
  notes: string;
  conductedAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateInterviewParams {
  companyId: string;
  workspaceId: string;
  projectId: string;
  contactRef?: string | number;
  notes: string;
  conductedAt?: string;
}

export interface ListInterviewsParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId?: string | number;
}

export interface UpdateInterviewParams {
  contactRef?: string | number;
  notes?: string;
  conductedAt?: string;
}

export const createInterview = api(
  { method: "POST", path: "/operations/strategy/interviews", expose: true },
  async (params: CreateInterviewParams): Promise<Interview> => {
    if (!params.workspaceId || !params.companyId || !params.projectId || !params.notes) {
      throw APIError.invalidArgument("companyId, workspaceId, projectId, and notes are required");
    }

    const [row] = await db
      .insert(interviews)
      .values({
        id: generateSnowflake(),
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        contactRef: params.contactRef ? BigInt(params.contactRef) : null,
        notes: params.notes,
        conductedAt: params.conductedAt ? new Date(params.conductedAt) : new Date(),
      })
      .returning();

    if (!row) throw APIError.internal("failed to create interview record");

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      contactRef: row.contactRef ? row.contactRef.toString() : null,
      notes: row.notes,
      conductedAt: row.conductedAt.toISOString(),
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getInterview = api(
  { method: "GET", path: "/operations/strategy/interviews/:id", expose: true },
  async ({ id }: { id: string }): Promise<Interview> => {
    const [row] = await db
      .select()
      .from(interviews)
      .where(and(eq(interviews.id, BigInt(id)), isNull(interviews.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`interview with id ${id} not found`);

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      contactRef: row.contactRef ? row.contactRef.toString() : null,
      notes: row.notes,
      conductedAt: row.conductedAt.toISOString(),
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listInterviews = api(
  { method: "GET", path: "/operations/strategy/interviews", expose: true },
  async (params: ListInterviewsParams): Promise<{ items: Interview[] }> => {
    const conditions = [isNull(interviews.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(interviews.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(interviews.companyId, BigInt(params.companyId)));
    }
    if (params.projectId) {
      conditions.push(eq(interviews.projectId, BigInt(params.projectId)));
    }

    const rows = await db
      .select()
      .from(interviews)
      .where(and(...conditions));

    return {
      items: rows.map((row) => ({
        id: row.id.toString(),
        companyId: row.companyId.toString(),
        workspaceId: row.workspaceId.toString(),
        projectId: row.projectId.toString(),
        contactRef: row.contactRef ? row.contactRef.toString() : null,
        notes: row.notes,
        conductedAt: row.conductedAt.toISOString(),
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateInterview = api(
  { method: "PATCH", path: "/operations/strategy/interviews/:id", expose: true },
  async ({ id, ...params }: UpdateInterviewParams & { id: string }): Promise<Interview> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.notes !== undefined) updateValues.notes = params.notes;
    if (params.contactRef !== undefined) {
      updateValues.contactRef = params.contactRef ? BigInt(params.contactRef) : null;
    }
    if (params.conductedAt !== undefined) updateValues.conductedAt = new Date(params.conductedAt);

    const [row] = await db
      .update(interviews)
      .set(updateValues)
      .where(and(eq(interviews.id, BigInt(id)), isNull(interviews.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`interview with id ${id} not found`);

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      contactRef: row.contactRef ? row.contactRef.toString() : null,
      notes: row.notes,
      conductedAt: row.conductedAt.toISOString(),
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const deleteInterview = api(
  { method: "DELETE", path: "/operations/strategy/interviews/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(interviews)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(interviews.id, BigInt(id)), isNull(interviews.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`interview with id ${id} not found`);
    return { success: true };
  }
);
