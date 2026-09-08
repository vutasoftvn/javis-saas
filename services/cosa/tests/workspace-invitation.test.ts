import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { registerPlatform } from "../handlers/auth.handler";
import { createCompanyFor, joinCompanyFor } from "../handlers/company.handler";
import {
  createWorkspaceInvitationFor,
  acceptWorkspaceInvitationFor,
} from "../handlers/company.handler";
import { verifyPlatformToken } from "../services/token.service";
import { db, schema } from "../models/db";

const { workspaceInvitations } = schema;

async function registerUser(prefix: string) {
  const email = `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}@example.com`;
  const res = await registerPlatform({
    email,
    password: "password1234",
    full_name: prefix,
  });
  return { email, userID: verifyPlatformToken(res.access_token).sub, accessToken: res.access_token };
}

async function createFounderWithCompany(prefix: string) {
  const founder = await registerUser(prefix);
  const company = await createCompanyFor({ userID: founder.userID }, { name: `${prefix} Co` });
  return { ...founder, companyId: company.company_id };
}

describe("Workspace Invitation Service (ADR-WORKSPACE-INVITATION-001)", () => {
  it("rejects joining an existing company via bare company_id even when the workspace id is known", async () => {
    const founder = await createFounderWithCompany("known_ws_founder");
    const stranger = await registerUser("known_ws_stranger");

    await expect(
      joinCompanyFor({ userID: stranger.userID }, { company_id: founder.companyId })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("lets the founder issue an invitation and the invited email accepts it", async () => {
    const founder = await createFounderWithCompany("issue_founder");
    const invitee = await registerUser("issue_invitee");

    const invitation = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: invitee.email, role_id: "member" }
    );

    expect(invitation.invitation_id).toBeDefined();
    expect(invitation.token).toBeDefined();
    expect(invitation.expires_at).toBeDefined();

    const accepted = await acceptWorkspaceInvitationFor(
      { userID: invitee.userID },
      { token: invitation.token }
    );

    expect(accepted.company_id).toBe(founder.companyId);
    expect(accepted.role_id).toBe("member");
  });

  it("rejects a non-member trying to issue an invitation for a workspace they don't belong to", async () => {
    const founder = await createFounderWithCompany("issuer_guard_founder");
    const outsider = await registerUser("issuer_guard_outsider");

    await expect(
      createWorkspaceInvitationFor(
        { userID: outsider.userID },
        { workspace_id: founder.companyId, email: "someone@example.com", role_id: "member" }
      )
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects issuing an invitation with a founder/co-founder role", async () => {
    const founder = await createFounderWithCompany("role_guard_founder");

    await expect(
      createWorkspaceInvitationFor(
        { userID: founder.userID },
        { workspace_id: founder.companyId, email: "future-cofounder@example.com", role_id: "founder" as any }
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("allows an admin (invited earlier) to issue further invitations", async () => {
    const founder = await createFounderWithCompany("admin_issue_founder");
    const admin = await registerUser("admin_issue_admin");

    const adminInvite = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: admin.email, role_id: "admin" }
    );
    await acceptWorkspaceInvitationFor({ userID: admin.userID }, { token: adminInvite.token });

    const nextInvitee = await registerUser("admin_issue_invitee");
    const nextInvite = await createWorkspaceInvitationFor(
      { userID: admin.userID },
      { workspace_id: founder.companyId, email: nextInvitee.email, role_id: "member" }
    );
    expect(nextInvite.token).toBeDefined();
  });

  it("rejects accept when the caller's email does not match the invitation email", async () => {
    const founder = await createFounderWithCompany("email_mismatch_founder");
    const invitee = await registerUser("email_mismatch_invitee");
    const intruder = await registerUser("email_mismatch_intruder");

    const invitation = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: invitee.email, role_id: "member" }
    );

    await expect(
      acceptWorkspaceInvitationFor({ userID: intruder.userID }, { token: invitation.token })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("creates exactly one membership on first accept, then is idempotent on retry", async () => {
    const founder = await createFounderWithCompany("idempotent_founder");
    const invitee = await registerUser("idempotent_invitee");

    const invitation = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: invitee.email, role_id: "member" }
    );

    const first = await acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token });
    expect(first.role_id).toBe("member");

    // Retry sau khi đã accept (network retry / double click) phải idempotent,
    // không tạo thêm membership thứ hai và không throw.
    const second = await acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token });
    expect(second.company_id).toBe(first.company_id);
    expect(second.role_id).toBe(first.role_id);
  });

  it("accepts the same token from concurrent callers with only one membership created", async () => {
    const founder = await createFounderWithCompany("concurrent_founder");
    const invitee = await registerUser("concurrent_invitee");

    const invitation = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: invitee.email, role_id: "member" }
    );

    const results = await Promise.allSettled([
      acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token }),
      acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token }),
      acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token }),
    ]);

    const fulfilled = results.filter((r) => r.status === "fulfilled");
    expect(fulfilled.length).toBe(3);

    const companies = await import("../handlers/company.handler").then((m) =>
      m.listMyCompaniesFor({ userID: invitee.userID })
    );
    const matches = companies.companies.filter((c) => c.company_id === founder.companyId);
    expect(matches.length).toBe(1);
  });

  it("rejects accept for a revoked invitation", async () => {
    const founder = await createFounderWithCompany("revoke_founder");
    const invitee = await registerUser("revoke_invitee");

    const invitation = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: invitee.email, role_id: "member" }
    );

    await db
      .update(workspaceInvitations)
      .set({ status: "revoked", revokedAt: new Date() })
      .where(eq(workspaceInvitations.id, BigInt(invitation.invitation_id)));

    await expect(
      acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects accept for an expired invitation", async () => {
    const founder = await createFounderWithCompany("expiry_founder");
    const invitee = await registerUser("expiry_invitee");

    const invitation = await createWorkspaceInvitationFor(
      { userID: founder.userID },
      { workspace_id: founder.companyId, email: invitee.email, role_id: "member" }
    );

    await db
      .update(workspaceInvitations)
      .set({ expiresAt: new Date(Date.now() - 60_000) })
      .where(eq(workspaceInvitations.id, BigInt(invitation.invitation_id)));

    await expect(
      acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: invitation.token })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects accept with a garbage token that does not match any invitation", async () => {
    const invitee = await registerUser("garbage_token_invitee");

    await expect(
      acceptWorkspaceInvitationFor({ userID: invitee.userID }, { token: "not-a-real-token" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
