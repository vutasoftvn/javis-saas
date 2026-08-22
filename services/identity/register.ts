import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";
import { hashPassword } from "./password";
import { signAccessToken } from "./token";

export interface RegisterParams {
  email: string;
  password: string;
  displayName?: string;
}

export interface RegisterResult {
  accessToken: string;
  userId: number;
  workspaceId: number;
}

export const registerUser = api(
  { method: "POST", path: "/identity/register", expose: true },
  async (params: RegisterParams): Promise<RegisterResult> => {
    const email = params.email.trim().toLowerCase();

    const existing = await identityDB.queryRow<{ id: number }>`
      SELECT id FROM core.users WHERE email = ${email}
    `;
    if (existing) {
      throw APIError.alreadyExists("email đã được đăng ký");
    }

    const passwordHash = await hashPassword(params.password);

    const tx = await identityDB.begin();
    try {
      const userRow = await tx.queryRow<{ id: number }>`
        INSERT INTO core.users (email, password_hash, display_name)
        VALUES (${email}, ${passwordHash}, ${params.displayName ?? null})
        RETURNING id
      `;
      if (!userRow) throw APIError.internal("failed to create user");

      const workspaceRow = await tx.queryRow<{ id: number }>`
        INSERT INTO core.workspaces (name)
        VALUES (${`Workspace của ${params.displayName ?? email}`})
        RETURNING id
      `;
      if (!workspaceRow) throw APIError.internal("failed to create workspace");

      await tx.exec`
        INSERT INTO core.workspace_members (workspace_id, user_id, role)
        VALUES (${workspaceRow.id}, ${userRow.id}, 'admin')
      `;

      await tx.commit();

      return {
        accessToken: signAccessToken(String(userRow.id)),
        userId: userRow.id,
        workspaceId: workspaceRow.id,
      };
    } catch (err) {
      await tx.rollback();
      throw err;
    }
  }
);
