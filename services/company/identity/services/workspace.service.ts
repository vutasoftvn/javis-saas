import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { identityWorkspaces } = schema;

export interface Workspace {
  id: string;
  name: string;
  companyStage: string;
  createdAt: string;
}

export interface CreateWorkspaceParams {
  name: string;
}

export async function createWorkspaceRecord(params: CreateWorkspaceParams): Promise<Workspace> {
  const [row] = await db
    .insert(identityWorkspaces)
    .values({
      id: generateSnowflake(),
      name: params.name,
    })
    .returning({
      id: identityWorkspaces.id,
      name: identityWorkspaces.name,
      companyStage: identityWorkspaces.companyStage,
      createdAt: identityWorkspaces.createdAt,
    });

  if (!row) throw APIError.internal("failed to create workspace");
  return {
    id: row.id.toString(),
    name: row.name,
    companyStage: row.companyStage,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getWorkspaceRecord(id: string | number): Promise<Workspace> {
  const [row] = await db
    .select({
      id: identityWorkspaces.id,
      name: identityWorkspaces.name,
      companyStage: identityWorkspaces.companyStage,
      createdAt: identityWorkspaces.createdAt,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workspace ${id} not found`);
  return {
    id: row.id.toString(),
    name: row.name,
    companyStage: row.companyStage,
    createdAt: row.createdAt.toISOString(),
  };
}
