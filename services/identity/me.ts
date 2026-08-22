import { api, APIError } from "encore.dev/api";
import { getAuthData } from "~encore/auth";
import { identityDB } from "./db";
import type { AuthData } from "./auth";

export interface MeResponse {
  id: number;
  email: string | null;
  displayName: string | null;
  workspaceId: number | null;
  role: string | null;
}

export async function getMe(auth: AuthData): Promise<MeResponse> {
  const userId = Number(auth.userID);
  const userRow = await identityDB.queryRow<{ id: number; email: string | null; display_name: string | null }>`
    SELECT id, email, display_name FROM core.users WHERE id = ${userId}
  `;
  if (!userRow) throw APIError.notFound("user not found");

  const membershipRow = await identityDB.queryRow<{ workspace_id: number; role: string }>`
    SELECT workspace_id, role FROM core.workspace_members WHERE user_id = ${userId} LIMIT 1
  `;

  return {
    id: userRow.id,
    email: userRow.email,
    displayName: userRow.display_name,
    workspaceId: membershipRow?.workspace_id ?? null,
    role: membershipRow?.role ?? null,
  };
}

export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async (): Promise<MeResponse> => getMe(getAuthData()!)
);
