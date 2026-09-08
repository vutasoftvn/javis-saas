import * as crypto from "node:crypto";
import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "./snowflake.service";
import { CompanyActionResponse } from "./company.service";

const {
  users,
  workspaces,
  workspaceMemberships,
  workspaceInvitations,
  workspaceSettingsAuditEvents,
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
  workspaceId: bigint,
  actorId: string,
  eventType: string,
  targetId: string,
  details: Record<string, unknown>
): Promise<void> {
  await client.insert(workspaceSettingsAuditEvents).values({
    eventId: BigInt(generateSnowflakeStr()),
    workspaceId,
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
  const workspaceId = BigInt(params.workspace_id);
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
    .where(and(eq(workspaces.id, workspaceId), eq(workspaces.status, "active")))
    .limit(1);
  if (!ws) {
    throw APIError.notFound("workspace không tồn tại hoặc đã bị vô hiệu hóa");
  }

  // Kiểm tra quyền issuer ở server (đọc role thực từ DB) — quyết định 4 của
  // ADR: chỉ founder/co-founder/admin của đúng workspace mới được issue.
  const [actorMembership] = await db
    .select({ roleId: workspaceMemberships.roleId })
    .from(workspaceMemberships)
    .where(and(eq(workspaceMemberships.workspaceId, workspaceId), eq(workspaceMemberships.userId, actorUserId)))
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
      workspaceId,
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

  await writeInvitationAuditEvent(db, workspaceId, actorId, "invitation.created", invitationId.toString(), {
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
 * Accept invitation bằng token thô. Transaction-safe: khoá đúng row invitation
 * qua `SELECT ... FOR UPDATE` để 2 accept song song cùng token chỉ tạo đúng
 * một membership (accept thứ hai sẽ thấy status đã "accepted" và trả về
 * idempotent — quyết định 7 + 8 của ADR).
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

  return db.transaction(async (tx) => {
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
      .where(eq(workspaces.id, invitation.workspaceId))
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
        .where(and(eq(workspaceMemberships.workspaceId, invitation.workspaceId), eq(workspaceMemberships.userId, actorUserId)))
        .limit(1);
      if (!existingMembership) {
        // Token đã accept nhưng không phải bởi principal hiện tại.
        throw APIError.permissionDenied("lời mời này đã được sử dụng");
      }
      return buildCompanyActionResponse(invitation.workspaceId, ws.name, existingMembership.roleId);
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

    const [existingMembership] = await tx
      .select({ roleId: workspaceMemberships.roleId })
      .from(workspaceMemberships)
      .where(and(eq(workspaceMemberships.workspaceId, invitation.workspaceId), eq(workspaceMemberships.userId, actorUserId)))
      .limit(1);

    let finalRoleId = invitation.roleId;
    if (existingMembership) {
      // Đã là member qua đường khác — không tạo row thứ hai, chỉ đánh dấu
      // invitation đã dùng.
      finalRoleId = existingMembership.roleId;
    } else {
      const newMembershipId = BigInt(generateSnowflakeStr());
      await tx.insert(workspaceMemberships).values({
        id: newMembershipId,
        workspaceId: invitation.workspaceId,
        userId: actorUserId,
        roleId: invitation.roleId,
      });
    }

    await tx
      .update(workspaceInvitations)
      .set({ status: "accepted", acceptedAt: now })
      .where(eq(workspaceInvitations.id, invitation.id));

    await writeInvitationAuditEvent(tx, invitation.workspaceId, actorId, "invitation.accepted", invitation.id.toString(), {
      email: invitation.emailNormalized,
      role_id: finalRoleId,
    });

    return buildCompanyActionResponse(invitation.workspaceId, ws.name, finalRoleId);
  });
}

function buildCompanyActionResponse(workspaceId: bigint, workspaceName: string, roleId: string): CompanyActionResponse {
  return {
    company_id: workspaceId.toString(),
    name: workspaceName,
    role_id: roleId,
    workspace: {
      workspace_id: workspaceId.toString(),
      workspace_name: workspaceName,
      role_id: roleId,
      status: "active",
    },
  };
}
