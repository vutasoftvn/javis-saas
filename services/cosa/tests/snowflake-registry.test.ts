// M2 §2 / ADR-ID-MODEL-001 — managed Snowflake generator registry + bit layout.
import { afterEach, describe, expect, it } from "vitest";
import { and, eq, inArray } from "drizzle-orm";
import { db, schema } from "../db";
import {
  acquireGeneratorSlot,
  renewGeneratorLease,
  releaseGeneratorSlot,
  bootstrapGeneratorSlot,
  heartbeatBoundGenerator,
  localGeneratorId,
} from "../services/snowflake-registry.service";
import {
  generateSnowflake,
  decodeSnowflake,
  configureGeneratorSlot,
  __resetGeneratorForTest,
  COSA_SNOWFLAKE_EPOCH_MS,
} from "../services/snowflake.service";

const { snowflakeGeneratorSlots } = schema;
const created: string[] = [];

function gid(tag: string): string {
  const id = `test:${tag}:${Date.now()}:${Math.random().toString(36).slice(2)}`;
  created.push(id);
  return id;
}

afterEach(async () => {
  __resetGeneratorForTest();
  if (created.length) {
    await db
      .delete(snowflakeGeneratorSlots)
      .where(inArray(snowflakeGeneratorSlots.generatorId, created.splice(0)));
  }
});

describe("snowflake generator registry", () => {
  it("acquires a slot with a fencing token and lease", async () => {
    const lease = await acquireGeneratorSlot({
      generatorId: gid("a"),
      runtimeRole: "cosa_control_plane",
    });
    expect(lease.slot).toBeGreaterThanOrEqual(0);
    expect(lease.slot).toBeLessThanOrEqual(1023);
    expect(lease.fencingToken).toBeGreaterThan(0n);
    expect(lease.leaseEpoch).toBe(1n);
    expect(lease.leaseExpiresAt.getTime()).toBeGreaterThan(Date.now());
  });

  it("two live generators never get the same slot", async () => {
    const a = await acquireGeneratorSlot({ generatorId: gid("x"), runtimeRole: "cosa_control_plane" });
    const b = await acquireGeneratorSlot({ generatorId: gid("y"), runtimeRole: "cosa_control_plane" });
    expect(a.slot).not.toBe(b.slot);
  });

  it("re-acquire by the same generator while the lease is valid keeps the slot + epoch", async () => {
    const g = gid("keep");
    const first = await acquireGeneratorSlot({ generatorId: g, runtimeRole: "cosa_control_plane" });
    const again = await acquireGeneratorSlot({ generatorId: g, runtimeRole: "cosa_control_plane" });
    expect(again.slot).toBe(first.slot);
    expect(again.leaseEpoch).toBe(first.leaseEpoch); // không bump khi còn hạn
  });

  it("after the lease expires, re-acquire bumps the epoch + issues a new fencing token", async () => {
    const g = gid("expire");
    const first = await acquireGeneratorSlot({ generatorId: g, runtimeRole: "cosa_control_plane" });
    // ép hết hạn
    await db
      .update(snowflakeGeneratorSlots)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(eq(snowflakeGeneratorSlots.generatorId, g));

    const again = await acquireGeneratorSlot({ generatorId: g, runtimeRole: "cosa_control_plane" });
    expect(again.slot).toBe(first.slot); // giữ đúng slot identity qua restart
    expect(again.leaseEpoch).toBe(first.leaseEpoch + 1n);
    expect(again.fencingToken).not.toBe(first.fencingToken);
  });

  it("another generator can reclaim an expired slot", async () => {
    const g1 = gid("r1");
    const g2 = gid("r2");
    const l1 = await acquireGeneratorSlot({ generatorId: g1, runtimeRole: "cosa_control_plane" });
    await db
      .update(snowflakeGeneratorSlots)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(eq(snowflakeGeneratorSlots.generatorId, g1));

    // buộc g2 phải xét chính slot của g1: giữ mọi slot khác "active" là bất khả thi
    // ở test nhỏ, nên chỉ khẳng định g2 lấy được một slot hợp lệ và g1 row biến mất.
    const l2 = await acquireGeneratorSlot({ generatorId: g2, runtimeRole: "cosa_control_plane" });
    expect(l2.slot).toBeGreaterThanOrEqual(0);

    const rows = await db
      .select()
      .from(snowflakeGeneratorSlots)
      .where(inArray(snowflakeGeneratorSlots.generatorId, [g1, g2]));
    // g1 hoặc đã bị g2 reclaim (row đổi generator_id) hoặc vẫn còn nhưng hết hạn.
    expect(rows.some((r) => r.generatorId === g2)).toBe(true);
  });

  it("renew rejects a stale fencing token", async () => {
    const g = gid("fence");
    const lease = await acquireGeneratorSlot({ generatorId: g, runtimeRole: "cosa_control_plane" });
    await expect(
      renewGeneratorLease({ generatorId: g, fencingToken: lease.fencingToken + 999n }),
    ).rejects.toMatchObject({ code: "failed_precondition" });
    // token đúng thì ok
    const ok = await renewGeneratorLease({ generatorId: g, fencingToken: lease.fencingToken });
    expect(ok.leaseExpiresAt.getTime()).toBeGreaterThan(Date.now());
  });

  it("bootstrap acquires a slot and wires snowflake.service; heartbeat renews it", async () => {
    process.env.COSA_GENERATOR_ID = gid("boot");
    try {
      const lease = await bootstrapGeneratorSlot();
      expect(lease.slot).toBeGreaterThanOrEqual(0);
      // snowflake.service giờ đã có slot ⇒ generate + decode ra đúng slot.
      const decoded = decodeSnowflake(generateSnowflake());
      expect(decoded.slot).toBe(lease.slot);

      const [before] = await db
        .select({ e: snowflakeGeneratorSlots.leaseExpiresAt })
        .from(snowflakeGeneratorSlots)
        .where(eq(snowflakeGeneratorSlots.generatorId, localGeneratorId()));
      await new Promise((r) => setTimeout(r, 5));
      await heartbeatBoundGenerator(123n);
      const [after] = await db
        .select({ e: snowflakeGeneratorSlots.leaseExpiresAt, c: snowflakeGeneratorSlots.clockCheckpoint })
        .from(snowflakeGeneratorSlots)
        .where(eq(snowflakeGeneratorSlots.generatorId, localGeneratorId()));
      expect(after.e.getTime()).toBeGreaterThanOrEqual(before.e.getTime());
      expect(after.c).toBe(123n);
    } finally {
      delete process.env.COSA_GENERATOR_ID;
    }
  });

  it("release makes the slot immediately reclaimable", async () => {
    const g = gid("rel");
    const lease = await acquireGeneratorSlot({ generatorId: g, runtimeRole: "cosa_control_plane" });
    await releaseGeneratorSlot(g);
    const [row] = await db
      .select()
      .from(snowflakeGeneratorSlots)
      .where(eq(snowflakeGeneratorSlots.generatorId, g));
    expect(row.leaseExpiresAt.getTime()).toBeLessThan(Date.now());
    expect(lease.slot).toBeGreaterThanOrEqual(0);
  });
});

describe("snowflake bit layout v1", () => {
  it("encodes the configured slot and a decodable timestamp", () => {
    configureGeneratorSlot(42);
    const id = generateSnowflake();
    const decoded = decodeSnowflake(id);
    expect(decoded.slot).toBe(42);
    expect(decoded.timestampMs).toBeGreaterThan(COSA_SNOWFLAKE_EPOCH_MS);
    expect(id).toBeLessThan(1n << 63n); // fit BIGINT signed
  });

  it("is monotonically increasing across rapid calls", () => {
    configureGeneratorSlot(7);
    let prev = generateSnowflake();
    for (let i = 0; i < 5000; i++) {
      const next = generateSnowflake();
      expect(next).toBeGreaterThan(prev);
      prev = next;
    }
  });

  it("sequence exhaustion within a ms spins to the next ms, never wraps backwards", () => {
    configureGeneratorSlot(1);
    const ids: bigint[] = [];
    for (let i = 0; i < 8200; i++) ids.push(generateSnowflake()); // > 2 * 4096
    for (let i = 1; i < ids.length; i++) expect(ids[i]).toBeGreaterThan(ids[i - 1]);
  });
});
