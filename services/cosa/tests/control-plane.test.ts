import { describe, it, expect } from "vitest";
import { getMe, updateMe } from "../handlers/auth.handler";
import {
  createCompanyFor,
  joinCompanyFor,
  listMyCompaniesFor,
  validateMembership,
  createWorkspaceInvitationFor,
  acceptWorkspaceInvitationFor,
} from "../handlers/company.handler";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { asCaller, registerPlatform, verifyPlatformToken } from "./support/test-identity";

const { workspaces, workspaceMemberships } = schema;

describe("Control Plane Service", () => {
  const testEmail = `founder_${Date.now()}@example.com`;
  let platformToken = "";
  let companyId = "";

  it("registers a platform user with a new company", async () => {
    const res = await registerPlatform({
      email: testEmail,
      password: "password1234",
      full_name: "John Doe",
      company_name: "Acme AI Corp",
    });

    expect(res.access_token).toBeDefined();
    expect(res.platform_workspace_id).toBeDefined();
    platformToken = res.access_token;
    companyId = res.platform_workspace_id!;

    const payload = verifyPlatformToken(res.access_token);
    expect(["cosa", "control_plane"]).toContain(payload.aud);
    expect(payload.sub).toBeDefined();
  });

  it("accepts registration with an 8-character password", async () => {
    const res = await registerPlatform({
      email: `valid_${Date.now()}@example.com`,
      password: "12345678",
      full_name: "Valid Password",
    });
    expect(res.access_token).toEqual(expect.any(String));
  });

  it("retrieves current platform user profile with founder role for company creator", async () => {
    const profile = await getMe(asCaller(verifyPlatformToken(platformToken).sub));

    expect(profile.email).toBe(testEmail);
    expect(profile.full_name).toBe("John Doe");
    expect(profile.role_id).toBe("founder");
    expect(profile.is_platform_admin).toBe(false);
  });

  it("updates COSA-owned persona fields but rejects core-owned contact fields", async () => {
    const caller = asCaller(verifyPlatformToken(platformToken).sub);
    const updated = await updateMe(caller, {
      headline: "Founder @ Cosa AI",
      bio: "Building next-gen AI workspace",
    });
    expect(updated.headline).toBe("Founder @ Cosa AI");
    expect(updated.bio).toBe("Building next-gen AI workspace");
    expect(updated.role_id).toBe("founder");

    // Spec 2026-09-25 §8 — phone/tên hiển thị thuộc Core, COSA không ghi.
    await expect(updateMe(caller, { full_name: "John Doe Updated" })).rejects.toMatchObject({
      code: "invalid_argument",
    });
    await expect(updateMe(caller, { phone: "+84912345678" })).rejects.toMatchObject({
      code: "invalid_argument",
    });
    const after = await getMe(caller);
    expect(after.full_name).toBe("John Doe");
  });

  it("does not mutate the global role from self-profile input", async () => {
    const caller = asCaller(verifyPlatformToken(platformToken).sub);
    const before = await getMe(caller);
    const updated = await updateMe(caller, { role_id: "superadmin" } as any);
    expect(updated.role_id).toBe(before.role_id);
  });

  it("rejects registration with duplicate email", async () => {
    await expect(
      registerPlatform({
        email: testEmail,
        password: "password1234",
        full_name: "Duplicate User",
      })
    ).rejects.toThrow();
  });

  it("lists companies of the platform user", async () => {
    const res = await listMyCompaniesFor(asCaller(verifyPlatformToken(platformToken).sub));

    expect(res.companies.length).toBeGreaterThanOrEqual(1);
    expect(res.companies[0].company_id).toBe(companyId);
    expect(res.companies[0].role_id).toBe("founder");
  });

  it("creates a second company", async () => {
    const secondComp = await createCompanyFor(
      asCaller(verifyPlatformToken(platformToken).sub),
      { name: "Second Venture Inc" }
    );

    expect(secondComp.company_id).toBeDefined();
    expect(secondComp.role_id).toBe("founder");
    expect(secondComp.name).toBe("Second Venture Inc");
  });

  // ADR-WORKSPACE-INVITATION-001 (Task 2): self-join bằng company_id trần
  // không còn là hành vi hợp lệ — trước đây test này document nó như thành
  // công, nay phải document đúng hành vi mới (từ chối). Luồng "join thật"
  // giờ nằm ở workspace-invitation.test.ts (issue → accept qua token).
  it("no longer allows joining an existing company via bare company_id", async () => {
    const newUserRes = await registerPlatform({
      email: `member_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Jane Member",
    });

    await expect(
      joinCompanyFor(
        asCaller(verifyPlatformToken(newUserRes.access_token).sub),
        { company_id: companyId }
      )
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  // Red test — chốt authority contract theo ADR-WORKSPACE-INVITATION-001.
  // Endpoint join-by-company-id hiện tại (`joinExistingCompany`) chỉ cần biết
  // `company_id` để tự cấp membership — không có invitation, không audit, không
  // người cấp quyền. Sau khi migrate sang invitation-only (Task 2+), gọi
  // `joinCompanyFor` với `company_id` trần PHẢI bị từ chối `permission_denied`.
  // Test này CỐ Ý fail ở implementation hiện tại — đó là bằng chứng của lỗ hổng,
  // không phải lỗi test.
  it("rejects a second user joining an existing company by bare company_id (no invitation)", async () => {
    const intruderRes = await registerPlatform({
      email: `intruder_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Uninvited Intruder",
    });

    await expect(
      joinCompanyFor(
        asCaller(verifyPlatformToken(intruderRes.access_token).sub),
        { company_id: companyId }
      )
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("validates membership via internal RPC", async () => {
    const validation = await validateMembership({
      platformToken,
      companyId,
    });

    expect(validation.valid).toBe(true);
    expect(validation.roleId).toBe("founder");
    expect(validation.companyName).toBe("Acme AI Corp");
    expect(validation.email).toBe(testEmail);
  });

  // Task 6 (ADR-WORKSPACE-INVITATION-001 hardening) — Snowflake IDs vượt quá
  // Number.MAX_SAFE_INTEGER (2^53-1). Nếu bất kỳ điểm nào trên đường đi
  // response (Encore.ts JSON serialize, Drizzle bigint column, hay code tay)
  // vô tình coi ID là `number` thay vì `bigint`/`string`, giá trị full
  // 19-chữ-số này sẽ bị làm tròn — test dùng đúng ID biên `2^63-1` trong brief
  // để chốt việc đó không xảy ra trên toàn bộ luồng invitation accept.
  it("preserves full 19-digit Snowflake precision through the invitation accept response (no Number() coercion)", async () => {
    const MAX_PRECISION_ID = 9223372036854775807n;

    const founderRes = await registerPlatform({
      email: `precision_founder_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Precision Founder",
    });
    const founderUserId = verifyPlatformToken(founderRes.access_token).sub;

    const inviteeEmail = `precision_invitee_${Date.now()}@example.com`;

    // Dọn trước nếu ID biên này còn sót lại từ lần chạy test trước (ID cố
    // định, không phải Snowflake sinh mới mỗi lần — CASCADE trên FK dọn luôn
    // memberships/invitations liên quan) để test idempotent qua nhiều lần chạy.
    await db.delete(workspaces).where(eq(workspaces.id, MAX_PRECISION_ID));

    // Tạo workspace trực tiếp với ID = giá trị biên 2^63-1 — provisioning
    // bình thường luôn sinh Snowflake mới nên không kiểm soát được đúng giá
    // trị biên; chèn thẳng để bài test xác định chính xác ID cần theo dõi.
    await db.insert(workspaces).values({
      id: MAX_PRECISION_ID,
      workspaceName: "Precision Co",
      ownerId: BigInt(founderUserId),
      status: "active",
    });
    await db.insert(workspaceMemberships).values({
      id: BigInt(`9223372036854775806`),
      organizationId: MAX_PRECISION_ID,
      userId: BigInt(founderUserId),
      roleId: "founder",
    });

    const invitation = await createWorkspaceInvitationFor(
      asCaller(founderUserId),
      {
        workspace_id: MAX_PRECISION_ID.toString(),
        email: inviteeEmail,
        role_id: "member",
      }
    );
    // invitation_id bản thân nó cũng là Snowflake — phải là string, và
    // JSON.stringify không được biến nó thành literal số.
    expect(typeof invitation.invitation_id).toBe("string");
    expect(JSON.stringify(invitation)).not.toMatch(/"invitation_id":\d/);

    const inviteeRes = await registerPlatform({
      email: inviteeEmail,
      password: "password1234",
      full_name: "Precision Invitee",
    });
    const inviteeUserId = verifyPlatformToken(inviteeRes.access_token).sub;

    const accepted = await acceptWorkspaceInvitationFor(
      asCaller(inviteeUserId),
      { token: invitation.token }
    );

    // Assertion chính: company_id trả về khớp CHÍNH XÁC chuỗi 19-chữ-số gốc —
    // nếu có Number() coercion ở đâu đó, giá trị này sẽ lệch (làm tròn thành
    // "9223372036854775808" hoặc mất độ chính xác dạng khác).
    expect(accepted.company_id).toBe("9223372036854775807");
    expect(accepted.workspace?.workspace_id).toBe("9223372036854775807");

    // Xác nhận JSON thực tế phía wire không bao giờ chứa ID này dưới dạng
    // literal số trần (không có dấu ngoặc kép bao quanh) — đây chính là dấu
    // hiệu của lỗi mất chính xác khi serialize qua `number`.
    const wire = JSON.stringify(accepted);
    expect(wire).toContain('"company_id":"9223372036854775807"');
    expect(wire).not.toMatch(/"company_id":9223372036854775807/);

    // listMyCompaniesFor cũng phải trả cùng ID dạng string chính xác.
    const companies = await listMyCompaniesFor(asCaller(inviteeUserId));
    const match = companies.companies.find((c) => c.company_id === "9223372036854775807");
    expect(match).toBeDefined();
    expect(JSON.stringify(companies)).not.toMatch(/"company_id":9223372036854775807/);
  });
});
