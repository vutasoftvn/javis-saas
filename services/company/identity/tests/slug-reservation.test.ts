// M2 §6 / ADR-SLUG-001 — reservation + rename qua DB thật.
import { describe, expect, it } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createWorkspace } from "../handlers/workspace.handler";
import { getWorkspaceRecord } from "../services/workspace.service";
import {
  reserveWorkspaceSlug,
  renameWorkspaceSlug,
  autoReserveSlugFromName,
} from "../services/slug-reservation.service";

const { identityWorkspaceSlugs } = schema;

async function bareWorkspace(name: string): Promise<bigint> {
  // Tạo workspace rồi xoá slug auto để test reserve từ trạng thái trống.
  const ws = await createWorkspace({ name });
  const id = BigInt(ws.id);
  await db.delete(identityWorkspaceSlugs).where(eq(identityWorkspaceSlugs.workspaceId, id));
  await db
    .update(schema.identityWorkspaces)
    .set({ slug: null })
    .where(eq(schema.identityWorkspaces.id, id));
  return id;
}

describe("workspace slug reservation", () => {
  it("createWorkspace auto-derives a slug from the name", async () => {
    const ws = await createWorkspace({ name: `Quốc Gia Khởi Nghiệp ${Date.now()}` });
    expect(ws.slug).toMatch(/^quoc-gia-khoi-nghiep/);
    const fetched = await getWorkspaceRecord(ws.id);
    expect(fetched.slug).toBe(ws.slug);
  });

  it("reserveWorkspaceSlug stores an ACTIVE row + sets workspace.slug", async () => {
    const id = await bareWorkspace(`Reserve Test ${Date.now()}`);
    const unique = `res-${Date.now()}`;
    const r = await reserveWorkspaceSlug({ workspaceId: id, requestedSlug: unique });
    expect(r.slug).toBe(unique);

    const [row] = await db
      .select()
      .from(identityWorkspaceSlugs)
      .where(
        and(
          eq(identityWorkspaceSlugs.workspaceId, id),
          eq(identityWorkspaceSlugs.status, "ACTIVE"),
        ),
      );
    expect(row.slug).toBe(unique);
    expect((await getWorkspaceRecord(id.toString())).slug).toBe(unique);
  });

  it("rejects an invalid / reserved slug", async () => {
    const id = await bareWorkspace(`Bad Slug ${Date.now()}`);
    await expect(
      reserveWorkspaceSlug({ workspaceId: id, requestedSlug: "admin" }),
    ).rejects.toThrow(/reserved/);
    await expect(
      reserveWorkspaceSlug({ workspaceId: id, requestedSlug: "💥" }),
    ).rejects.toThrow(/không hợp lệ/);
  });

  it("concurrent reservation of the same slug — only one wins", async () => {
    const a = await bareWorkspace(`Race A ${Date.now()}`);
    const b = await bareWorkspace(`Race B ${Date.now()}`);
    const wanted = `race-${Date.now()}`;

    const results = await Promise.allSettled([
      reserveWorkspaceSlug({ workspaceId: a, requestedSlug: wanted }),
      reserveWorkspaceSlug({ workspaceId: b, requestedSlug: wanted }),
    ]);
    const fulfilledExact = results.filter(
      (r) => r.status === "fulfilled" && r.value.slug === wanted,
    );
    expect(fulfilledExact).toHaveLength(1);
  });

  it("rename keeps workspace_id, marks old slug REDIRECT, points to the new one", async () => {
    const id = await bareWorkspace(`Rename Test ${Date.now()}`);
    const first = `rn-${Date.now()}-a`;
    const second = `rn-${Date.now()}-b`;
    await reserveWorkspaceSlug({ workspaceId: id, requestedSlug: first });
    await renameWorkspaceSlug({ workspaceId: id, newSlug: second });

    const rows = await db
      .select()
      .from(identityWorkspaceSlugs)
      .where(eq(identityWorkspaceSlugs.workspaceId, id));
    const oldRow = rows.find((r) => r.slug === first)!;
    const newRow = rows.find((r) => r.slug === second)!;
    expect(oldRow.status).toBe("REDIRECT");
    expect(oldRow.redirectToSlug).toBe(second);
    expect(newRow.status).toBe("ACTIVE");
    expect((await getWorkspaceRecord(id.toString())).slug).toBe(second);
  });

  it("rename to a slug owned by another workspace is rejected", async () => {
    const a = await bareWorkspace(`Own A ${Date.now()}`);
    const b = await bareWorkspace(`Own B ${Date.now()}`);
    const taken = `own-${Date.now()}`;
    await reserveWorkspaceSlug({ workspaceId: a, requestedSlug: taken });
    await reserveWorkspaceSlug({ workspaceId: b, requestedSlug: `${taken}-b` });
    await expect(
      renameWorkspaceSlug({ workspaceId: b, newSlug: taken }),
    ).rejects.toThrow(/đã được dùng/);
  });

  it("autoReserveSlugFromName falls back to a numeric suffix on collision", async () => {
    const shared = `dup-${Date.now()}`;
    const a = await bareWorkspace("Dup A");
    const b = await bareWorkspace("Dup B");
    const sa = await autoReserveSlugFromName(a, shared);
    const sb = await autoReserveSlugFromName(b, shared);
    expect(sa).toBe(shared);
    expect(sb).toBe(`${shared}-2`);
  });
});
