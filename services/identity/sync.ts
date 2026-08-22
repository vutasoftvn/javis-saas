import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";
import { signAccessToken } from "./token";
import { validateMembership } from "../control-plane/company";

export interface SyncFromPlatformParams {
  platform_access_token?: string;
  platformAccessToken?: string;
  company_id?: string | number;
  companyId?: string | number;
}

export interface SyncFromPlatformResult {
  access_token: string;
  token_type: string;
}

export const syncFromPlatform = api(
  { method: "POST", path: "/identity/sync-from-platform", expose: true },
  async (params: SyncFromPlatformParams): Promise<SyncFromPlatformResult> => {
    const token = params.platform_access_token || params.platformAccessToken;
    const compId = params.company_id || params.companyId;

    if (!token || !compId) {
      throw APIError.invalidArgument("vui lòng cung cấp platform_access_token và company_id");
    }

    const member = await validateMembership({
      platformToken: token,
      companyId: String(compId),
    });

    const tx = await identityDB.begin();
    try {
      // 1. Tim hoac tao local user tuong ung voi platform user nay
      let localUser = await tx.queryRow<{ id: number; email: string | null }>`
        SELECT id, email FROM core.users WHERE platform_user_id = ${member.userId}
      `;

      if (!localUser && member.email) {
        localUser = await tx.queryRow<{ id: number; email: string | null }>`
          SELECT id, email FROM core.users WHERE LOWER(email) = ${member.email.toLowerCase()}
        `;
      }

      let localUserId: number;

      if (!localUser) {
        const created = await tx.queryRow<{ id: number }>`
          INSERT INTO core.users (email, phone, display_name, platform_user_id, role)
          VALUES (${member.email}, ${member.phone}, ${member.displayName}, ${member.userId}, ${member.roleId})
          RETURNING id
        `;
        if (!created) throw APIError.internal("failed to create local user");
        localUserId = created.id;
      } else {
        localUserId = localUser.id;
        await tx.exec`
          UPDATE core.users
          SET platform_user_id = ${member.userId},
              role = ${member.roleId},
              display_name = COALESCE(display_name, ${member.displayName})
          WHERE id = ${localUserId}
        `;
      }

      // 2. Tim hoac tao workspace local cho company nay
      let workspace = await tx.queryRow<{ id: number }>`
        SELECT id FROM core.workspaces WHERE platform_company_id = ${member.companyId}
      `;

      let isNewWorkspace = false;
      let workspaceId: number;

      if (!workspace) {
        isNewWorkspace = true;
        const createdWorkspace = await tx.queryRow<{ id: number }>`
          INSERT INTO core.workspaces (name, platform_company_id)
          VALUES (${member.companyName}, ${member.companyId})
          RETURNING id
        `;
        if (!createdWorkspace) throw APIError.internal("failed to create workspace");
        workspaceId = createdWorkspace.id;
      } else {
        workspaceId = workspace.id;
      }

      // 3. Gan membership trong workspace
      const existingMember = await tx.queryRow<{ id: number }>`
        SELECT id FROM core.workspace_members
        WHERE workspace_id = ${workspaceId} AND user_id = ${localUserId}
      `;

      if (!existingMember) {
        await tx.exec`
          INSERT INTO core.workspace_members (workspace_id, user_id, role)
          VALUES (${workspaceId}, ${localUserId}, ${isNewWorkspace ? "admin" : "member"})
        `;
      }

      await tx.commit();

      const localAccessToken = signAccessToken(String(localUserId));
      return {
        access_token: localAccessToken,
        token_type: "bearer",
      };
    } catch (err) {
      await tx.rollback();
      throw err;
    }
  }
);
