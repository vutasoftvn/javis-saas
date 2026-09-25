import * as crypto from "node:crypto";
import { APIError } from "encore.dev/api";
import { and, asc, eq, inArray, lt, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "./snowflake.service";
import { CompanyActionResponse } from "./company.service";
import { grantCoreMembership, type CoreMembershipGrant } from "./core-organization.service";
import { mapCoreRoleToCosaRole } from "./core-projection.service";

const {
  users,
  workspaces,
  workspaceMemberships,
  workspaceInvitations,
  workspaceSettingsAuditEvents,
  organizationInvitationGrants,
} = schema;

/**
 * ADR-WORKSPACE-INVITATION-001 — invitation có hạn thay cho self-join bằng
 * `company_id` trần. Token thô chỉ được trả về đúng một lần lúc tạo; chỉ
 * SHA-256 hash được lưu trong DB (`token_hash`). Xem ADR để biết đầy đủ lý do
 * cho từng quyết định dưới đây — mọi giá trị (168h expiry, role giới hạn
 * member/admin, single-use, idempotent retry-after-accept) là contract chốt,
 * không phải mặc định tự chọn khi code.
 */

// Nhận diện unique-violation Postgres (SQLSTATE 23505) xuyên qua chuỗi
// `.cause` (driver `pg` có thể bọc lỗi) — chỉ khi khớp mã này mới được coi là
// "đã tồn tại", tránh gán nhầm nghĩa cho lỗi DB khác (deadlock, transient...).
// Cùng pattern với snowflake-registry.service.ts / runtime-node-registry.service.ts.
function isUniqueViolation(err: unknown): boolean {
  let cur: unknown = err;
  for (let d = 0; d < 5 && cur; d++) {
    if (typeof cur === "object" && cur !== null) {
      const o = cur as { code?: string; message?: string; cause?: unknown };
      if (o.code === "23505") return true;
      if (typeof o.message === "string" && o.message.includes("duplicate key value")) return true;
      cur = o.cause;
    } else break;
  }
  return false;
}

export type InvitationRole = "member" | "admin";

const ISSUER_ALLOWED_ROLES = new Set(["founder", "co-founder", "admin"]);
const INVITATION_ALLOWED_ROLES = new Set<InvitationRole>(["member", "admin"]);
const DEFAULT_EXPIRES_IN_HOURS = 168;

export interface CreateWorkspaceInvitationParams {
  workspace_id: string;
  email: string;
  role_id: InvitationRole;
  expires_in_hours?: number;
}

export interface CreateWorkspaceInvitationResponse {
  invitation_id: string;
  token: string;
  expires_at: string;
}

export interface AcceptWorkspaceInvitationParams {
  token: string;
}

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

function hashToken(rawToken: string): string {
  return crypto.createHash("sha256").update(rawToken).digest("hex");
}

type DbOrTx = Pick<typeof db, "insert">;

async function writeInvitationAuditEvent(
  client: DbOrTx,
  organizationId: bigint,
  actorId: string,
  eventType: string,
  targetId: string,
  details: Record<string, unknown>
): Promise<void> {
  await client.insert(workspaceSettingsAuditEvents).values({
    eventId: BigInt(generateSnowflakeStr()),
    organizationId,
    actorId,
    eventType,
    targetKind: "workspace_invitation",
    targetId,
    details,
  });
}

/**
 * Founder/co-founder/admin của đúng workspace phát hành invitation cho một
 * email cụ thể. Role cấp cho invitation chỉ giới hạn `member` hoặc `admin` —
 * không bao giờ `founder`/`co-founder` (quyết định 3 của ADR).
 */
export async function createWorkspaceInvitation(
  actorId: string,
  params: CreateWorkspaceInvitationParams
): Promise<CreateWorkspaceInvitationResponse> {
  const actorUserId = BigInt(actorId);
  const organizationId = BigInt(params.workspace_id);
  const email = normalizeEmail(params.email);

  if (!email || !email.includes("@")) {
    throw APIError.invalidArgument("email không hợp lệ");
  }
  if (!INVITATION_ALLOWED_ROLES.has(params.role_id)) {
    throw APIError.invalidArgument("role_id chỉ có thể là 'member' hoặc 'admin'");
  }

  const [ws] = await db
    .select({ id: workspaces.id })
    .from(workspaces)
    .where(and(eq(workspaces.id, organizationId), eq(workspaces.status, "active")))
    .limit(1);
  if (!ws) {
    throw APIError.notFound("workspace không tồn tại hoặc đã bị vô hiệu hóa");
  }

  // Kiểm tra quyền issuer ở server (đọc role thực từ DB) — quyết định 4 của
  // ADR: chỉ founder/co-founder/admin của đúng workspace mới được issue.
  const [actorMembership] = await db
    .select({ roleId: workspaceMemberships.roleId })
    .from(workspaceMemberships)
    .where(and(eq(workspaceMemberships.organizationId, organizationId), eq(workspaceMemberships.userId, actorUserId)))
    .limit(1);

  if (!actorMembership || !ISSUER_ALLOWED_ROLES.has(actorMembership.roleId)) {
    throw APIError.permissionDenied("chỉ founder, co-founder hoặc admin của workspace mới được mời thành viên mới");
  }

  const expiresInHours = params.expires_in_hours ?? DEFAULT_EXPIRES_IN_HOURS;
  if (!Number.isFinite(expiresInHours) || expiresInHours <= 0) {
    throw APIError.invalidArgument("expires_in_hours phải là số dương");
  }

  const rawToken = crypto.randomBytes(32).toString("base64url");
  const tokenHash = hashToken(rawToken);
  const invitationId = BigInt(generateSnowflakeStr());
  const now = new Date();
  const expiresAt = new Date(now.getTime() + expiresInHours * 60 * 60 * 1000);

  // Idempotent theo (workspace_id, email) khi còn "pending" nhờ unique index
  // một phần trong migration 34 — insert trùng sẽ raise lỗi DB.
  try {
    await db.insert(workspaceInvitations).values({
      id: invitationId,
      organizationId,
      emailNormalized: email,
      roleId: params.role_id,
      tokenHash,
      status: "pending",
      invitedByUserId: actorUserId,
      expiresAt,
    });
  } catch (err) {
    // Chỉ coi là "đã tồn tại lời mời" khi đúng unique-violation Postgres
    // (23505) trên (workspace_id, email_normalized) — lỗi DB khác (deadlock,
    // transient, constraint không liên quan) không được gán nhầm nghĩa này.
    if (isUniqueViolation(err)) {
      throw APIError.alreadyExists("đã tồn tại lời mời đang chờ cho email này trong workspace");
    }
    throw APIError.internal("không thể tạo lời mời do lỗi hệ thống, vui lòng thử lại");
  }

  await writeInvitationAuditEvent(db, organizationId, actorId, "invitation.created", invitationId.toString(), {
    email,
    role_id: params.role_id,
    expires_at: expiresAt.toISOString(),
  });

  return {
    invitation_id: invitationId.toString(),
    token: rawToken,
    expires_at: expiresAt.toISOString(),
  };
}

/**
 * Accept invitation bằng token thô — saga với core (spec 2026-09-25 §8):
 *  1. Transaction cục bộ: khoá invitation, kiểm tra, ghi ý định `requested`
 *     (unique theo invitation) TRƯỚC khi gọi core.
 *  2. Gọi core (idempotent) NGOÀI transaction; lỗi chỉ ghi attempts/mã lỗi,
 *     invitation vẫn `pending` để thử lại hoặc để reconciler xử lý.
 *  3. Ghi `core_granted` ở transaction riêng, rồi `projectInvitationGrant`
 *     chiếu membership + đánh dấu invitation `accepted` (`projected`).
 * Retry sau accept thành công trả về membership hiện có (ADR quyết định 7 + 8).
 */
export async function acceptWorkspaceInvitation(
  actorId: string,
  params: AcceptWorkspaceInvitationParams
): Promise<CompanyActionResponse> {
  const actorUserId = BigInt(actorId);
  const tokenHash = hashToken(params.token);

  const [actor] = await db
    .select({ email: users.email })
    .from(users)
    .where(eq(users.id, actorUserId))
    .limit(1);
  if (!actor) {
    throw APIError.notFound("platform user không tồn tại");
  }
  const actorEmail = actor.email ? normalizeEmail(actor.email) : null;

  const prepared = await db.transaction(async (tx): Promise<
    { kind: "done"; response: CompanyActionResponse } | { kind: "grant"; grant: InvitationGrantRow }
  > => {
    const [invitation] = await tx
      .select()
      .from(workspaceInvitations)
      .where(eq(workspaceInvitations.tokenHash, tokenHash))
      .for("update");

    if (!invitation) {
      throw APIError.permissionDenied("lời mời không tồn tại hoặc token không hợp lệ");
    }

    const [ws] = await tx
      .select({ id: workspaces.id, name: workspaces.workspaceName })
      .from(workspaces)
      .where(eq(workspaces.id, invitation.organizationId))
      .limit(1);
    if (!ws) {
      throw APIError.notFound("workspace của lời mời không còn tồn tại");
    }

    // Retry sau accept thành công (hoặc principal đã là member qua đường
    // khác) phải trả về membership hiện có, không insert bản ghi thứ hai.
    if (invitation.status === "accepted") {
      const [existingMembership] = await tx
        .select({ roleId: workspaceMemberships.roleId })
        .from(workspaceMemberships)
        .where(and(eq(workspaceMemberships.organizationId, invitation.organizationId), eq(workspaceMemberships.userId, actorUserId)))
        .limit(1);
      if (!existingMembership) {
        // Token đã accept nhưng không phải bởi principal hiện tại.
        throw APIError.permissionDenied("lời mời này đã được sử dụng");
      }
      return {
        kind: "done",
        response: buildCompanyActionResponse(invitation.organizationId, ws.name, existingMembership.roleId),
      };
    }

    if (invitation.status === "revoked") {
      throw APIError.permissionDenied("lời mời đã bị thu hồi");
    }

    if (invitation.status === "expired") {
      throw APIError.permissionDenied("lời mời đã hết hạn");
    }

    // status === "pending" từ đây trở xuống.
    const now = new Date();
    if (invitation.expiresAt <= now) {
      await tx
        .update(workspaceInvitations)
        .set({ status: "expired" })
        .where(eq(workspaceInvitations.id, invitation.id));
      throw APIError.permissionDenied("lời mời đã hết hạn");
    }

    if (!actorEmail || actorEmail !== invitation.emailNormalized) {
      throw APIError.permissionDenied("email của bạn không khớp với lời mời này");
    }

    // Ghi ý định trước khi gọi core; retry dùng lại đúng bản ghi này.
    const [inserted] = await tx
      .insert(organizationInvitationGrants)
      .values({
        id: BigInt(generateSnowflakeStr()),
        invitationId: invitation.id,
        organizationId: invitation.organizationId,
        userId: actorUserId,
        requestedRole: invitation.roleId,
        state: "requested",
      })
      .onConflictDoNothing({ target: organizationInvitationGrants.invitationId })
      .returning();
    let grant = inserted;
    if (inserted) {
      await writeInvitationAuditEvent(tx, invitation.organizationId, actorId, "invitation.grant_requested", invitation.id.toString(), {
        email: invitation.emailNormalized,
        role_id: invitation.roleId,
      });
    } else {
      [grant] = await tx
        .select()
        .from(organizationInvitationGrants)
        .where(eq(organizationInvitationGrants.invitationId, invitation.id))
        .limit(1);
    }
    if (!grant || grant.userId !== actorUserId) {
      throw APIError.permissionDenied("lời mời này đang được xử lý cho người dùng khác");
    }
    return { kind: "grant", grant };
  });

  if (prepared.kind === "done") return prepared.response;

  let grant = prepared.grant;
  if (grant.state === "requested" || grant.state === "failed") {
    grant = await requestCoreGrant(grant, actorId);
  }
  return projectInvitationGrant(grant.id);
}

type InvitationGrantRow = typeof organizationInvitationGrants.$inferSelect;

function errorCodeOf(err: unknown): string {
  if (err instanceof APIError) return err.code;
  if (err && typeof err === "object" && "code" in err && typeof err.code === "string") return err.code;
  return "unknown";
}

/** Gọi core (idempotent) và ghi `core_granted`; lỗi chỉ ghi attempts + mã lỗi rồi ném lại. */
async function requestCoreGrant(grant: InvitationGrantRow, actorId: string): Promise<InvitationGrantRow> {
  let granted: CoreMembershipGrant;
  try {
    granted = await grantCoreMembership(grant.organizationId.toString(), grant.userId.toString(), grant.requestedRole);
  } catch (err) {
    // Không suy ra thành công từ timeout: giữ `requested` để retry/reconcile.
    await db
      .update(organizationInvitationGrants)
      .set({
        state: "requested",
        attempts: sql`${organizationInvitationGrants.attempts} + 1`,
        lastErrorCode: errorCodeOf(err),
        updatedAt: new Date(),
      })
      .where(eq(organizationInvitationGrants.id, grant.id));
    throw err;
  }

  return db.transaction(async (tx) => {
    const [updated] = await tx
      .update(organizationInvitationGrants)
      .set({
        state: "core_granted",
        coreRole: granted.role,
        coreMembershipVersion: granted.membershipVersion ?? null,
        attempts: sql`${organizationInvitationGrants.attempts} + 1`,
        lastErrorCode: null,
        updatedAt: new Date(),
      })
      .where(eq(organizationInvitationGrants.id, grant.id))
      .returning();
    await writeInvitationAuditEvent(tx, grant.organizationId, actorId, "invitation.core_granted", grant.invitationId.toString(), {
      core_role: granted.role,
      core_membership_version: granted.membershipVersion ?? null,
    });
    return updated ?? grant;
  });
}

/**
 * Chiếu membership cục bộ theo role core đã cấp, đánh dấu invitation
 * `accepted` và grant `projected`. Idempotent: gọi lại trên grant đã
 * `projected` chỉ trả về membership hiện có.
 */
export async function projectInvitationGrant(grantId: bigint): Promise<CompanyActionResponse> {
  return db.transaction(async (tx) => {
    const [grant] = await tx
      .select()
      .from(organizationInvitationGrants)
      .where(eq(organizationInvitationGrants.id, grantId))
      .for("update");
    if (!grant) throw APIError.notFound("invitation grant không tồn tại");
    if (grant.state !== "core_granted" && grant.state !== "projected") {
      throw APIError.failedPrecondition(`invitation grant chưa được core xác nhận (state=${grant.state})`);
    }

    const [ws] = await tx
      .select({ name: workspaces.workspaceName })
      .from(workspaces)
      .where(eq(workspaces.id, grant.organizationId))
      .limit(1);
    if (!ws) throw APIError.notFound("workspace của lời mời không còn tồn tại");

    const coreRoleId = mapCoreRoleToCosaRole(grant.coreRole ?? grant.requestedRole);
    const now = new Date();

    const [existingMembership] = await tx
      .select({ roleId: workspaceMemberships.roleId })
      .from(workspaceMemberships)
      .where(and(eq(workspaceMemberships.organizationId, grant.organizationId), eq(workspaceMemberships.userId, grant.userId)))
      .limit(1);

    if (grant.state === "projected" && existingMembership) {
      return buildCompanyActionResponse(grant.organizationId, ws.name, existingMembership.roleId);
    }

    if (existingMembership) {
      // Đã là member qua đường khác — không tạo row thứ hai, chỉ đồng bộ role theo core.
      if (coreRoleId !== existingMembership.roleId) {
        await tx
          .update(workspaceMemberships)
          .set({ roleId: coreRoleId, updatedAt: now })
          .where(and(eq(workspaceMemberships.organizationId, grant.organizationId), eq(workspaceMemberships.userId, grant.userId)));
      }
    } else {
      await tx.insert(workspaceMemberships).values({
        id: BigInt(generateSnowflakeStr()),
        organizationId: grant.organizationId,
        userId: grant.userId,
        roleId: coreRoleId,
      });
    }

    const [invitation] = await tx
      .update(workspaceInvitations)
      .set({ status: "accepted", acceptedAt: now })
      .where(and(eq(workspaceInvitations.id, grant.invitationId), eq(workspaceInvitations.status, "pending")))
      .returning({ emailNormalized: workspaceInvitations.emailNormalized });

    await tx
      .update(organizationInvitationGrants)
      .set({ state: "projected", updatedAt: now })
      .where(eq(organizationInvitationGrants.id, grant.id));

    await writeInvitationAuditEvent(tx, grant.organizationId, grant.userId.toString(), "invitation.accepted", grant.invitationId.toString(), {
      ...(invitation ? { email: invitation.emailNormalized } : {}),
      role_id: coreRoleId,
      grant_state: "projected",
    });

    return buildCompanyActionResponse(grant.organizationId, ws.name, coreRoleId);
  });
}

export interface InvitationGrantReconcileResult {
  scanned: number;
  projected: number;
  failed: number;
  pending: number;
}

/**
 * Reconciler có giới hạn cho grant còn dở (spec 2026-09-25 §8): `core_granted`
 * → chiếu; `requested` → hỏi lại core bằng đúng organization/user đã ghi
 * (grant idempotent) nếu invitation còn hiệu lực, ngược lại đánh dấu `failed`.
 * Lỗi mạng giữ nguyên trạng thái, không suy ra thành công.
 */
export async function reconcileInvitationGrants(
  options: { limit?: number; minAgeMs?: number } = {}
): Promise<InvitationGrantReconcileResult> {
  const limit = options.limit ?? 50;
  const cutoff = new Date(Date.now() - (options.minAgeMs ?? 60_000));
  const rows = await db
    .select()
    .from(organizationInvitationGrants)
    .where(
      and(
        inArray(organizationInvitationGrants.state, ["requested", "core_granted"]),
        lt(organizationInvitationGrants.updatedAt, cutoff)
      )
    )
    .orderBy(asc(organizationInvitationGrants.updatedAt))
    .limit(limit);

  const result: InvitationGrantReconcileResult = { scanned: rows.length, projected: 0, failed: 0, pending: 0 };
  for (const row of rows) {
    try {
      let grant = row;
      if (grant.state === "requested") {
        const [invitation] = await db
          .select({ status: workspaceInvitations.status, expiresAt: workspaceInvitations.expiresAt })
          .from(workspaceInvitations)
          .where(eq(workspaceInvitations.id, grant.invitationId))
          .limit(1);
        if (!invitation || invitation.status !== "pending" || invitation.expiresAt <= new Date()) {
          await db
            .update(organizationInvitationGrants)
            .set({ state: "failed", lastErrorCode: "invitation_not_pending", updatedAt: new Date() })
            .where(eq(organizationInvitationGrants.id, grant.id));
          await writeInvitationAuditEvent(db, grant.organizationId, "system:reconciler", "invitation.grant_failed", grant.invitationId.toString(), {
            reason: "invitation_not_pending",
          });
          result.failed += 1;
          continue;
        }
        grant = await requestCoreGrant(grant, "system:reconciler");
      }
      await projectInvitationGrant(grant.id);
      await writeInvitationAuditEvent(db, grant.organizationId, "system:reconciler", "invitation.reconciled", grant.invitationId.toString(), {});
      result.projected += 1;
    } catch {
      result.pending += 1;
    }
  }
  return result;
}

function buildCompanyActionResponse(organizationId: bigint, workspaceName: string, roleId: string): CompanyActionResponse {
  return {
    company_id: organizationId.toString(),
    name: workspaceName,
    role_id: roleId,
    workspace: {
      workspace_id: organizationId.toString(),
      workspace_name: workspaceName,
      role_id: roleId,
      status: "active",
    },
  };
}
