# Boundary Hardening Phase 0 — Hard Rule Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five specific violations of hard architectural rules (no direct DB queries in handlers; no raw `Error` throws in services) without changing API contracts or behavior.

**Architecture:** Encore.ts handlers must delegate all DB I/O to corresponding `services/` modules. Services must raise typed `APIError` instead of raw `Error`. This enforces the single-responsibility boundary: handlers parse input + call service + format response; services own business logic + DB transactions.

**Tech Stack:** TypeScript/Encore, Drizzle ORM, vitest (with `describe`, `it`, `expect`, `beforeEach`, `afterEach`, `vi`), database transactions for atomicity.

## Global Constraints

- Không đổi API contract: route path, request/response schema, HTTP status codes phải giữ nguyên.
- Không đổi hành vi: tất cả logic vẫn chạy đúng như trước, chỉ di chuyển vị trí code trong architecture.
- Mỗi giai đoạn commit riêng: sau khi test xanh, commit task này với message prefix rõ ràng.
- Test trước, code sau: viết failing test trước, chạy để xác nhận lỗi, rồi mới implement.
- Không dùng placeholder: tất cả function name, type, file path phải là thực tế đã đọc từ repo.

---

## Task 1: Move Channel Endpoint DB Queries to Service

**Files:**
- Modify: `services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts:64-94, 106-164, 176-196, 246-272`
- Modify/Create: `services/company/commercial/services/customer-engagement/channel-endpoints.service.ts` (new file)
- Test: `services/company/commercial/tests/channel-endpoints.service.test.ts`

**Interfaces:**
- Consumes: `engagementChannelEndpoints`, `engagementOutboundDeliveries` schema tables, `resolveVerificationConfig()`, `assertConnectorGrant()`
- Produces: `createChannelEndpoint()`, `activateChannelEndpoint()`, `pauseChannelEndpoint()`, `listChannelDeliveries()`, `retryChannelDelivery()` service functions

**Description:** The handler currently executes `db.insert()`, `db.select()`, `db.update()` directly (lines 64-78, 106-114, 147-151, 176-185, 246-260). Move each operation into a dedicated service function.

- [ ] **Step 1: Write the failing test**

Create `services/company/commercial/tests/channel-endpoints.service.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, schema } from "../../models/db";
import {
  createChannelEndpoint,
  activateChannelEndpoint,
  pauseChannelEndpoint,
  listChannelDeliveries,
  retryChannelDelivery,
} from "../services/customer-engagement/channel-endpoints.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

const mockCtx: TenantContext = {
  workspaceId: "ws_123",
  workforceMemberId: "member_456",
  platformWorkspaceId: "pws_123",
};

describe("Channel Endpoints Service", () => {
  beforeEach(async () => {
    await db.delete(schema.engagementOutboundDeliveries);
    await db.delete(schema.engagementChannelEndpoints);
  });

  afterEach(async () => {
    await db.delete(schema.engagementOutboundDeliveries);
    await db.delete(schema.engagementChannelEndpoints);
  });

  it("createChannelEndpoint inserts row and returns with string IDs", async () => {
    const result = await createChannelEndpoint({
      workspaceId: mockCtx.workspaceId,
      inboxId: "inbox_789",
      providerRef: "slack",
      connectorKey: "key_abc",
      verificationConfigRef: "cfg_001",
      autoCreateContact: false,
      skewSeconds: 300,
    });

    expect(result.id).toBeDefined();
    expect(result.workspaceId).toBe(mockCtx.workspaceId);
    expect(result.status).toBe("pending");
  });

  it("activateChannelEndpoint throws notFound when endpoint missing", async () => {
    await expect(
      activateChannelEndpoint({
        workspaceId: mockCtx.workspaceId,
        id: "nonexistent_123",
      }, mockCtx)
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("pauseChannelEndpoint updates status to paused", async () => {
    const created = await createChannelEndpoint({
      workspaceId: mockCtx.workspaceId,
      inboxId: "inbox_789",
      providerRef: "slack",
      connectorKey: "key_abc",
      verificationConfigRef: "cfg_001",
    });

    const result = await pauseChannelEndpoint({
      workspaceId: mockCtx.workspaceId,
      id: created.id,
    });

    expect(result.status).toBe("paused");
  });

  it("listChannelDeliveries returns deliveries filtered by workspace and status", async () => {
    // Setup: insert a delivery record
    const [delivery] = await db
      .insert(schema.engagementOutboundDeliveries)
      .values({
        id: BigInt("1"),
        workspaceId: BigInt(mockCtx.workspaceId),
        messageId: BigInt("2"),
        channelType: "slack",
        status: "sent",
      })
      .returning();

    const result = await listChannelDeliveries({
      workspaceId: mockCtx.workspaceId,
      status: "sent",
    });

    expect(result.deliveries.length).toBeGreaterThanOrEqual(1);
    expect(result.deliveries[0].status).toBe("sent");
  });

  it("retryChannelDelivery throws notFound when delivery missing", async () => {
    await expect(
      retryChannelDelivery({
        workspaceId: mockCtx.workspaceId,
        id: "nonexistent_delivery",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/commercial/tests/channel-endpoints.service.test.ts`

Expected: FAIL because `channel-endpoints.service.ts` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `services/company/commercial/services/customer-engagement/channel-endpoints.service.ts`:

```typescript
import { APIError } from "encore.dev/api";
import { and, eq, desc } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementChannelEndpoints,
  engagementOutboundDeliveries,
} from "../../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../../shared/services/snowflake.service";
import { resolveVerificationConfig } from "./channel-adapters/verification";
import { assertConnectorGrant } from "./connector-grant.client";

export async function createChannelEndpoint(input: {
  workspaceId: string;
  inboxId: string;
  providerRef: string;
  connectorKey: string;
  inboundRoutingKey?: string;
  verificationConfigRef?: string;
  autoCreateContact?: boolean;
  skewSeconds?: number;
}) {
  const wsId = BigInt(input.workspaceId);
  const inboxId = BigInt(input.inboxId);
  const id = generateSnowflake();

  const [row] = await db
    .insert(engagementChannelEndpoints)
    .values({
      id,
      workspaceId: wsId,
      inboxId,
      providerRef: input.providerRef,
      connectorKey: input.connectorKey,
      inboundRoutingKey: input.inboundRoutingKey,
      verificationConfigRef: input.verificationConfigRef,
      autoCreateContact: input.autoCreateContact ?? false,
      skewSeconds: input.skewSeconds ?? 300,
      status: "pending",
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    inboxId: row.inboxId.toString(),
    providerRef: row.providerRef,
    connectorKey: row.connectorKey,
    inboundRoutingKey: row.inboundRoutingKey,
    verificationConfigRef: row.verificationConfigRef,
    status: row.status,
    autoCreateContact: row.autoCreateContact,
    skewSeconds: row.skewSeconds,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export async function activateChannelEndpoint(input: {
  workspaceId: string;
  id: string;
}, ctx: any) {
  const wsId = BigInt(input.workspaceId);
  const epId = BigInt(input.id);

  const rows = await db
    .select()
    .from(engagementChannelEndpoints)
    .where(
      and(
        eq(engagementChannelEndpoints.id, epId),
        eq(engagementChannelEndpoints.workspaceId, wsId)
      )
    );

  if (rows.length === 0) {
    throw APIError.notFound("Channel endpoint not found");
  }

  const endpoint = rows[0];

  if (!endpoint.verificationConfigRef) {
    throw APIError.failedPrecondition("Endpoint missing verificationConfigRef");
  }
  try {
    await resolveVerificationConfig(endpoint.verificationConfigRef);
  } catch (err: any) {
    throw APIError.failedPrecondition(`Cannot activate endpoint: ${err.message}`);
  }

  if (!endpoint.connectorKey) {
    throw APIError.failedPrecondition("Endpoint missing connectorKey");
  }
  const grantRes = await assertConnectorGrant({
    workspaceId: input.workspaceId,
    conversationId: "system",
    connectorKey: endpoint.connectorKey,
    action: "send",
  });
  if (!grantRes.ok) {
    throw APIError.failedPrecondition(`Cannot activate endpoint: connector grant assertion failed for key ${endpoint.connectorKey}`);
  }

  const [updated] = await db
    .update(engagementChannelEndpoints)
    .set({ status: "active", updatedAt: new Date() })
    .where(eq(engagementChannelEndpoints.id, epId))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    inboxId: updated.inboxId.toString(),
    providerRef: updated.providerRef,
    connectorKey: updated.connectorKey,
    inboundRoutingKey: updated.inboundRoutingKey,
    verificationConfigRef: updated.verificationConfigRef,
    status: updated.status,
    updatedAt: updated.updatedAt,
  };
}

export async function pauseChannelEndpoint(input: {
  workspaceId: string;
  id: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const epId = BigInt(input.id);

  const [updated] = await db
    .update(engagementChannelEndpoints)
    .set({ status: "paused", updatedAt: new Date() })
    .where(
      and(
        eq(engagementChannelEndpoints.id, epId),
        eq(engagementChannelEndpoints.workspaceId, wsId)
      )
    )
    .returning();

  if (!updated) {
    throw APIError.notFound("Channel endpoint not found");
  }

  return {
    id: updated.id.toString(),
    status: updated.status,
    updatedAt: updated.updatedAt,
  };
}

export async function listChannelDeliveries(input: {
  workspaceId: string;
  id?: string;
  status?: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const conditions = [eq(engagementOutboundDeliveries.workspaceId, wsId)];
  if (input.status) {
    conditions.push(eq(engagementOutboundDeliveries.status, input.status));
  }

  const rows = await db
    .select()
    .from(engagementOutboundDeliveries)
    .where(and(...conditions))
    .orderBy(desc(engagementOutboundDeliveries.createdAt))
    .limit(100);

  return {
    deliveries: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      messageId: r.messageId.toString(),
      channelType: r.channelType,
      status: r.status,
      attemptCount: r.attemptCount,
      maxAttempts: r.maxAttempts,
      lastError: r.lastError,
      deadLetterReason: r.deadLetterReason,
      externalMessageId: r.externalMessageId,
      createdAt: r.createdAt,
    })),
  };
}

export async function retryChannelDelivery(input: {
  workspaceId: string;
  id: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const deliveryId = BigInt(input.id);

  const [updated] = await db
    .update(engagementOutboundDeliveries)
    .set({
      status: "queued",
      deadLetterReason: null,
      visibilityTimeoutAt: new Date(),
      claimToken: null,
    })
    .where(
      and(
        eq(engagementOutboundDeliveries.id, deliveryId),
        eq(engagementOutboundDeliveries.workspaceId, wsId)
      )
    )
    .returning();

  if (!updated) {
    throw APIError.notFound("Delivery not found");
  }

  return {
    id: updated.id.toString(),
    status: updated.status,
    attemptCount: updated.attemptCount,
    deadLetterReason: updated.deadLetterReason,
  };
}
```

Now update the handler to call these service functions instead of executing DB queries directly.

Update `services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts`:

```typescript
import { api, Header, APIError } from "encore.dev/api";
import {
  requireEngagementPermission,
  ENGAGEMENT_PERMISSIONS,
} from "../../services/customer-engagement/rbac";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import * as channelEndpointSvc from "../../services/customer-engagement/channel-endpoints.service";

export interface CreateChannelEndpointParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  inboxId: string;
  providerRef: string;
  connectorKey: string;
  inboundRoutingKey?: string;
  verificationConfigRef?: string;
  autoCreateContact?: boolean;
  skewSeconds?: number;
}

// ... other param interfaces ...

export const createChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels" },
  async (params: CreateChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.createChannelEndpoint({
      workspaceId: params.workspaceId,
      inboxId: params.inboxId,
      providerRef: params.providerRef,
      connectorKey: params.connectorKey,
      inboundRoutingKey: params.inboundRoutingKey,
      verificationConfigRef: params.verificationConfigRef,
      autoCreateContact: params.autoCreateContact,
      skewSeconds: params.skewSeconds,
    });
  }
);

export const activateChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/:id/activate" },
  async (params: ActivateChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.activateChannelEndpoint(
      { workspaceId: params.workspaceId, id: params.id },
      ctx
    );
  }
);

export const pauseChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/:id/pause" },
  async (params: PauseChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.pauseChannelEndpoint({
      workspaceId: params.workspaceId,
      id: params.id,
    });
  }
);

export const listChannelDeliveriesApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/channels/:id/deliveries" },
  async (params: ListChannelDeliveriesParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);

    return channelEndpointSvc.listChannelDeliveries({
      workspaceId: params.workspaceId,
      id: params.id,
      status: params.status,
    });
  }
);

export const retryChannelDeliveryApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/deliveries/:id/retry" },
  async (params: RetryChannelDeliveryParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.retryChannelDelivery({
      workspaceId: params.workspaceId,
      id: params.id,
    });
  }
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/commercial/tests/channel-endpoints.service.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add \
  services/company/commercial/services/customer-engagement/channel-endpoints.service.ts \
  services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts \
  services/company/commercial/tests/channel-endpoints.service.test.ts
git commit -m "refactor(commercial): move channel endpoint DB queries to service layer

Move db.insert/select/update calls from channel-admin handler into new
channel-endpoints.service (createChannelEndpoint, activateChannelEndpoint,
pauseChannelEndpoint, listChannelDeliveries, retryChannelDelivery).
Handler now delegates to service, preserving all error handling and behavior.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Move Automation Application DB Queries to Service

**Files:**
- Modify: `services/company/commercial/handlers/customer-engagement/automation.handler.ts:143-171`
- Modify: `services/company/commercial/services/customer-engagement/automation/applications.service.ts` (new file)
- Test: `services/company/commercial/tests/automation-applications.service.test.ts`

**Interfaces:**
- Consumes: `engagementAutomationApplications` schema table
- Produces: `listThreadAutomationApplications()` service function

**Description:** The `listThreadAutomationApplicationsApi` handler queries `engagementAutomationApplications` directly (lines 143–152). Extract into a service function.

- [ ] **Step 1: Write the failing test**

Create `services/company/commercial/tests/automation-applications.service.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, schema } from "../../models/db";
import { listThreadAutomationApplications } from "../services/customer-engagement/automation/applications.service";

describe("Automation Applications Service", () => {
  beforeEach(async () => {
    await db.delete(schema.engagementAutomationApplications);
  });

  afterEach(async () => {
    await db.delete(schema.engagementAutomationApplications);
  });

  it("listThreadAutomationApplications returns applications for workspace and thread", async () => {
    const wsId = BigInt("100");
    const threadId = BigInt("200");
    
    // Insert test application
    await db
      .insert(schema.engagementAutomationApplications)
      .values({
        id: BigInt("1"),
        workspaceId: wsId,
        threadId,
        ruleKey: "rule_001",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        actionType: "send_message",
        dedupeKey: "dedup_1",
        outcome: "succeeded",
      });

    const result = await listThreadAutomationApplications({
      workspaceId: "100",
      threadId: "200",
    });

    expect(result.applications.length).toBe(1);
    expect(result.applications[0].ruleKey).toBe("rule_001");
    expect(result.applications[0].actionType).toBe("send_message");
  });

  it("listThreadAutomationApplications returns empty for non-existent thread", async () => {
    const result = await listThreadAutomationApplications({
      workspaceId: "100",
      threadId: "999",
    });

    expect(result.applications).toEqual([]);
  });

  it("listThreadAutomationApplications filters by workspace", async () => {
    const wsId1 = BigInt("100");
    const wsId2 = BigInt("101");
    const threadId = BigInt("200");
    
    await db
      .insert(schema.engagementAutomationApplications)
      .values({
        id: BigInt("1"),
        workspaceId: wsId1,
        threadId,
        ruleKey: "rule_001",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        actionType: "send_message",
      });

    await db
      .insert(schema.engagementAutomationApplications)
      .values({
        id: BigInt("2"),
        workspaceId: wsId2,
        threadId,
        ruleKey: "rule_002",
        ruleVersion: 1,
        trigger: "thread_opened",
        actionIndex: 0,
        actionType: "assign_thread",
      });

    const result = await listThreadAutomationApplications({
      workspaceId: "100",
      threadId: "200",
    });

    expect(result.applications.length).toBe(1);
    expect(result.applications[0].ruleKey).toBe("rule_001");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/commercial/tests/automation-applications.service.test.ts`

Expected: FAIL because `applications.service.ts` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `services/company/commercial/services/customer-engagement/automation/applications.service.ts`:

```typescript
import { eq, and, desc } from "drizzle-orm";
import { db } from "../../../db";
import { engagementAutomationApplications } from "../../../../../shared/db/schema/customer-engagement";

export async function listThreadAutomationApplications(input: {
  workspaceId: string;
  threadId: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const threadId = BigInt(input.threadId);

  const rows = await db
    .select()
    .from(engagementAutomationApplications)
    .where(
      and(
        eq(engagementAutomationApplications.workspaceId, wsId),
        eq(engagementAutomationApplications.threadId, threadId)
      )
    )
    .orderBy(desc(engagementAutomationApplications.createdAt));

  return {
    applications: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      ruleKey: r.ruleKey,
      ruleVersion: r.ruleVersion,
      threadId: r.threadId.toString(),
      trigger: r.trigger,
      actionIndex: r.actionIndex,
      actionType: r.actionType,
      dedupeKey: r.dedupeKey,
      outcome: r.outcome,
      detail: r.detail,
      createdAt: r.createdAt,
    })),
  };
}
```

Update `services/company/commercial/handlers/customer-engagement/automation.handler.ts` to use the service:

Replace the `listThreadAutomationApplicationsApi` implementation with:

```typescript
import * as applicationsSvc from "../../services/customer-engagement/automation/applications.service";

export const listThreadAutomationApplicationsApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/threads/:id/automation/applications" },
  async (params: ListThreadApplicationsParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);

    return applicationsSvc.listThreadAutomationApplications({
      workspaceId: params.workspaceId,
      threadId: params.id,
    });
  }
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/commercial/tests/automation-applications.service.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add \
  services/company/commercial/services/customer-engagement/automation/applications.service.ts \
  services/company/commercial/handlers/customer-engagement/automation.handler.ts \
  services/company/commercial/tests/automation-applications.service.test.ts
git commit -m "refactor(commercial): move automation applications DB queries to service layer

Move db.select call from listThreadAutomationApplicationsApi handler into new
applications.service (listThreadAutomationApplications). Handler now delegates
to service, preserving all filtering and response formatting.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Move Workspace Schedule DB Queries to Service

**Files:**
- Modify: `services/cosa/handlers/workspace-schedule.handler.ts:81-90, 118-127`
- Modify: `services/cosa/services/workspace-schedule.service.ts` (add two functions)
- Test: `services/cosa/tests/workspace-schedule-handler.test.ts` (already exists; verify passing)

**Interfaces:**
- Consumes: `workspaceScheduleDefinitions`, `workspaceScheduleExecutions` schema tables
- Produces: `listWorkspaceSchedules()`, `getScheduleExecution()` service functions (add to existing service)

**Description:** The `listSchedulesEndpoint` (lines 81–90) and `getScheduleExecutionEndpoint` (lines 118–127) query `workspaceScheduleDefinitions` and `workspaceScheduleExecutions` directly. Extract these into workspace-schedule.service.ts which already handles other schedule operations.

- [ ] **Step 1: Write the failing test**

Add tests to `services/cosa/tests/workspace-schedule-handler.test.ts` (tests already exist for handler authorization; add two service-layer tests):

```typescript
describe("Workspace Schedule Service", () => {
  it("listWorkspaceSchedules returns schedules for workspace", async () => {
    const created = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily report",
    });

    const result = await scheduleSvc.listWorkspaceSchedules("ws_a");
    expect(result.items).toContainEqual(
      expect.objectContaining({ id: created.id })
    );
  });

  it("getScheduleExecution returns execution by ID", async () => {
    const schedule = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Scan",
    });

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: schedule.id,
      workspaceId: "ws_a",
      principalId: "user_a",
    });

    const result = await scheduleSvc.getScheduleExecution(execution.id);
    expect(result.id).toBe(execution.id);
  });

  it("getScheduleExecution throws notFound when execution missing", async () => {
    await expect(
      scheduleSvc.getScheduleExecution("nonexistent_exec_999")
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/cosa/tests/workspace-schedule-handler.test.ts`

Expected: FAIL on the new tests because `listWorkspaceSchedules()` and `getScheduleExecution()` do not exist in the service yet.

- [ ] **Step 3: Write minimal implementation**

Add these two functions to `services/cosa/services/workspace-schedule.service.ts` (before the exports, after the existing functions):

```typescript
export async function listWorkspaceSchedules(
  workspaceId: string
): Promise<{ items: any[]; total: number }> {
  const items = await db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(eq(workspaceScheduleDefinitions.workspaceId, workspaceId))
    .orderBy(desc(workspaceScheduleDefinitions.createdAt));

  return { items, total: items.length };
}

export async function getScheduleExecution(executionId: string): Promise<any> {
  const [execution] = await db
    .select()
    .from(workspaceScheduleExecutions)
    .where(eq(workspaceScheduleExecutions.id, executionId));

  if (!execution) {
    throw APIError.notFound("schedule execution not found");
  }
  return execution;
}
```

Update `services/cosa/handlers/workspace-schedule.handler.ts` to call the service functions:

Replace `listSchedulesEndpoint`:

```typescript
export const listSchedulesEndpoint = api(
  { method: "GET", path: "/cosa/schedules", expose: true },
  async (params: ListSchedulesParams) => {
    if (!params.authorization) throw APIError.unauthenticated("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    verifyPlatformToken(token);

    await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);

    return scheduleSvc.listWorkspaceSchedules(params.workspaceId);
  }
);
```

Replace `getScheduleExecutionEndpoint`:

```typescript
export const getScheduleExecutionEndpoint = api(
  { method: "GET", path: "/cosa/schedules/executions/:executionId", expose: true },
  async (params: { authorization?: Header<"Authorization">; executionId: string }) => {
    requireWorkerServiceAuth(params.authorization);

    return scheduleSvc.getScheduleExecution(params.executionId);
  }
);
```

Remove the direct DB imports at the top:

```typescript
// Delete this line:
// import { db, schema } from "../models/db";
// Delete this line:
// const { workspaceScheduleDefinitions, workspaceScheduleExecutions } = schema;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/cosa/tests/workspace-schedule-handler.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add \
  services/cosa/services/workspace-schedule.service.ts \
  services/cosa/handlers/workspace-schedule.handler.ts \
  services/cosa/tests/workspace-schedule-handler.test.ts
git commit -m "refactor(cosa): move schedule list/get DB queries to service layer

Add listWorkspaceSchedules() and getScheduleExecution() to
workspace-schedule.service. Update listSchedulesEndpoint and
getScheduleExecutionEndpoint handlers to delegate to service instead of
executing db.select directly. No API contract changes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Replace Raw Error with APIError in platform.client.ts

**Files:**
- Modify: `services/company/identity/services/platform.client.ts:13, 24`
- Test: `services/company/identity/tests/platform-client.test.ts` (create or extend existing)

**Interfaces:**
- Consumes: `APIError` (already imported)
- Produces: `APIError.internal()` throws instead of raw `Error`

**Description:** Lines 13 and 24 throw raw `Error`. These are configuration validation errors that fail at startup if secrets are misconfigured in staging/production. Replace with `APIError.internal()`.

- [ ] **Step 1: Write the failing test**

Create `services/company/identity/tests/platform-client.test.ts`:

```typescript
import { describe, it, expect, afterEach } from "vitest";

describe("platform.client configuration errors", () => {
  const prevSecret = process.env.PLATFORM_JWT_SECRET;
  const prevUrl = process.env.PLATFORM_API_BASE_URL;
  const prevEnv = process.env.NODE_ENV;

  afterEach(() => {
    if (prevSecret === undefined) delete process.env.PLATFORM_JWT_SECRET;
    else process.env.PLATFORM_JWT_SECRET = prevSecret;
    if (prevUrl === undefined) delete process.env.PLATFORM_API_BASE_URL;
    else process.env.PLATFORM_API_BASE_URL = prevUrl;
    if (prevEnv === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = prevEnv;
  });

  it("throws APIError.internal when PLATFORM_JWT_SECRET too short in prod", () => {
    process.env.NODE_ENV = "production";
    process.env.PLATFORM_JWT_SECRET = "short";

    // Import must happen after env setup
    const { getPlatformJwtSecret } = require("../services/platform.client");

    expect(() => getPlatformJwtSecret()).toThrow(
      expect.objectContaining({ code: "internal" })
    );
  });

  it("throws APIError.internal when PLATFORM_API_BASE_URL uses dev default in prod", () => {
    process.env.NODE_ENV = "production";
    process.env.PLATFORM_API_BASE_URL = "http://127.0.0.1:4001";

    const { getPlatformUrl } = require("../services/platform.client");

    expect(() => getPlatformUrl()).toThrow(
      expect.objectContaining({ code: "internal" })
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/identity/tests/platform-client.test.ts`

Expected: FAIL because `getPlatformJwtSecret()` and `getPlatformUrl()` throw raw `Error`, not `APIError.internal()`.

- [ ] **Step 3: Write minimal implementation**

Update `services/company/identity/services/platform.client.ts`:

```typescript
import jwt from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";

const DEV_PLATFORM_JWT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod";
const DEV_PLATFORM_URL = "http://127.0.0.1:4001";
const PLATFORM_REQUEST_TIMEOUT_MS = 5000;

function getPlatformJwtSecret(): string {
  const secret = process.env.PLATFORM_JWT_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_PLATFORM_JWT_SECRET || secret.length < 32) {
      throw APIError.internal("PLATFORM_JWT_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_PLATFORM_JWT_SECRET;
}

function getPlatformUrl(): string {
  const url = process.env.PLATFORM_API_BASE_URL;
  if (isStagingOrProd()) {
    if (!url || url === DEV_PLATFORM_URL) {
      throw APIError.internal("PLATFORM_API_BASE_URL must be explicitly set in staging/production, cannot use default URL");
    }
    return url;
  }
  return url || DEV_PLATFORM_URL;
}

// ... rest of file unchanged ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/identity/tests/platform-client.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add \
  services/company/identity/services/platform.client.ts \
  services/company/identity/tests/platform-client.test.ts
git commit -m "fix(company): replace raw Error with APIError in platform.client

Replace throw new Error() with throw APIError.internal() in
getPlatformJwtSecret and getPlatformUrl validation checks. These are
startup configuration errors that should be typed as internal server errors.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Replace Raw Error with APIError in token.service.ts

**Files:**
- Modify: `services/company/identity/services/token.service.ts:65, 73, 78`
- Test: `services/company/identity/tests/session-renew.test.ts` (update existing)

**Interfaces:**
- Consumes: `APIError` (import from encore.dev/api)
- Produces: `APIError.unauthenticated()` for token verification failures

**Description:** Lines 65, 73, 78 in `renewAccessToken()` throw raw `Error` when token validation fails. These are authentication failures and should be `APIError.unauthenticated()`. Note: line 39 already correctly uses `APIError.unauthenticated()` in `verifyAccessToken()`, so follow that pattern.

- [ ] **Step 1: Write the failing test**

Add tests to existing `services/company/identity/tests/session-renew.test.ts`:

```typescript
it("renewAccessToken throws APIError.unauthenticated for token with no subject", () => {
  const tokenNoSub = jwt.sign({}, JWT_SECRET, { expiresIn: "1h" });
  expect(() => renewAccessToken(tokenNoSub)).toThrow(
    expect.objectContaining({ code: "unauthenticated" })
  );
});

it("renewAccessToken throws APIError.unauthenticated when exceeds max age", () => {
  process.env.COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS = "60"; // 1 minute
  const oldToken = jwt.sign(
    { sub: "user_1", auth_time: Math.floor(Date.now() / 1000) - 120 },
    JWT_SECRET,
    { expiresIn: "24h" }
  );
  expect(() => renewAccessToken(oldToken)).toThrow(
    expect.objectContaining({ code: "unauthenticated" })
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/identity/tests/session-renew.test.ts`

Expected: FAIL because `renewAccessToken()` throws raw `Error`, not `APIError.unauthenticated()`.

- [ ] **Step 3: Write minimal implementation**

Update `services/company/identity/services/token.service.ts`:

```typescript
import jwt from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";

// ... existing code unchanged through line 50 ...

export function renewAccessToken(token: string): string {
  let sub: string;
  let authTime: number | undefined;
  try {
    const decoded = jwt.verify(token, getJwtSecret()) as jwt.JwtPayload & JwtPayload;
    sub = decoded.sub;
    authTime = decoded.auth_time;
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      const decoded = jwt.verify(token, getJwtSecret(), {
        ignoreExpiration: true,
      }) as jwt.JwtPayload & JwtPayload;
      const expMs = (decoded.exp ?? 0) * 1000;
      if (Date.now() - expMs > getRenewGraceSeconds() * 1000) {
        throw APIError.unauthenticated("local session expired beyond renewal grace window");
      }
      sub = decoded.sub;
      authTime = decoded.auth_time;
    } else {
      throw err;
    }
  }
  if (!sub) {
    throw APIError.unauthenticated("local session token has no subject");
  }
  // Chặn renewal chain vượt quá tuổi tối đa kể từ lần đăng nhập gốc — token
  // cũ trước khi có claim auth_time (authTime === undefined) được coi như vừa
  // đăng nhập lại để không phá vỡ session đang hoạt động của người dùng cũ.
  if (authTime !== undefined && Date.now() / 1000 - authTime > getMaximumSessionAgeSeconds()) {
    throw APIError.unauthenticated("local session exceeds maximum age");
  }
  return signAccessToken(sub, authTime);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/SSD/javis-saas && pnpm test --run services/company/identity/tests/session-renew.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add \
  services/company/identity/services/token.service.ts \
  services/company/identity/tests/session-renew.test.ts
git commit -m "fix(company): replace raw Error with APIError in token.service

Replace throw new Error() with throw APIError.unauthenticated() in
renewAccessToken() validation checks (expired beyond grace window,
missing subject, exceeds max age). Aligns with verifyAccessToken()
pattern which already uses APIError.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Verification Checklist

After all 5 tasks are committed:

- [ ] Run full test suite for services/company and services/cosa:
  ```bash
  cd /Volumes/SSD/javis-saas && pnpm test --run services/company services/cosa
  ```
  Expected: All tests PASS

- [ ] Verify no remaining direct DB calls in the 3 handlers:
  ```bash
  grep -n "db\\.insert\\|db\\.select\\|db\\.update\\|db\\.delete" \
    services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts \
    services/company/commercial/handlers/customer-engagement/automation.handler.ts \
    services/cosa/handlers/workspace-schedule.handler.ts
  ```
  Expected: No matches (or only matches in imports/comments)

- [ ] Verify no raw `Error` throws in the 2 service files:
  ```bash
  grep -n "throw new Error" \
    services/company/identity/services/platform.client.ts \
    services/company/identity/services/token.service.ts
  ```
  Expected: No matches

- [ ] Run type check:
  ```bash
  cd /Volumes/SSD/javis-saas && pnpm tsc --noEmit
  ```
  Expected: No errors

---

## Summary

5 tasks fix hard architectural rule violations:
1. **channel-admin.handler.ts** → new `channel-endpoints.service.ts` (5 DB operations)
2. **automation.handler.ts** → new `applications.service.ts` (1 DB operation)
3. **workspace-schedule.handler.ts** → extend `workspace-schedule.service.ts` (2 DB operations)
4. **platform.client.ts** → APIError.internal (2 raw Error throws)
5. **token.service.ts** → APIError.unauthenticated (3 raw Error throws)

All changes are internal refactors — no API contract, behavior, or schema changes. Each task is committed separately with passing tests.
