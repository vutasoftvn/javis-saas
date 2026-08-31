import { describe, it, expect } from "vitest";
import { recordTaskExecutionService, TaskExecutionRecordView } from "../services/task-execution-record.service";
import { createTask } from "../handlers/task.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

describe("Task Execution Record Service", () => {
  it("records a task execution with minimal parameters", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Test task",
      authorization: ws.bearerToken,
    });

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
    });

    expect(record).toBeDefined();
    expect(record.id).toBeDefined();
    expect(typeof record.id).toBe("string");
    expect(record.workspaceId).toBe(ws.workspaceId);
    expect(record.taskId).toBe(task.id);
    expect(record.capabilityId).toBe("test-capability");
    expect(record.triggeredByKind).toBe("system");
    expect(record.status).toBe("SUCCESS");
    expect(record.runId).toBeNull();
    expect(record.toolCallId).toBeNull();
    expect(record.decisionRecordId).toBeNull();
    expect(record.errorDetails).toBeNull();
  });

  it("records a task execution with all parameters including optional ones", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Complex task",
      authorization: ws.bearerToken,
    });

    const errorDetails = { code: "VALIDATION_ERROR", message: "Invalid input" };

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      runId: "run-123",
      toolCallId: "tool-456",
      capabilityId: "advanced-capability",
      triggeredByKind: "agent",
      status: "FAILED",
      errorDetails,
    });

    expect(record).toBeDefined();
    expect(record.workspaceId).toBe(ws.workspaceId);
    expect(record.taskId).toBe(task.id);
    expect(record.runId).toBe("run-123");
    expect(record.toolCallId).toBe("tool-456");
    expect(record.capabilityId).toBe("advanced-capability");
    expect(record.triggeredByKind).toBe("agent");
    expect(record.decisionRecordId).toBeNull();
    expect(record.status).toBe("FAILED");
    expect(record.errorDetails).toEqual(errorDetails);
  });

  it("supports all valid triggeredByKind values", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Multi-kind task",
      authorization: ws.bearerToken,
    });

    const kinds = ["agent", "founder", "workflow", "system"] as const;

    for (const kind of kinds) {
      const record = await recordTaskExecutionService({
        workspaceId: BigInt(ws.workspaceId),
        taskId: BigInt(task.id),
        capabilityId: `capability-${kind}`,
        triggeredByKind: kind,
      });

      expect(record.triggeredByKind).toBe(kind);
    }
  });

  it("defaults status to SUCCESS when not provided", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Default status task",
      authorization: ws.bearerToken,
    });

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
    });

    expect(record.status).toBe("SUCCESS");
  });

  it("allows explicit FAILED status", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Failed task",
      authorization: ws.bearerToken,
    });

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
      status: "FAILED",
    });

    expect(record.status).toBe("FAILED");
  });

  it("generates a unique Snowflake ID for each record", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Unique ID task",
      authorization: ws.bearerToken,
    });

    const record1 = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "capability-1",
      triggeredByKind: "system",
    });

    const record2 = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "capability-2",
      triggeredByKind: "system",
    });

    expect(record1.id).not.toBe(record2.id);
    expect(typeof record1.id).toBe("string");
    expect(typeof record2.id).toBe("string");
  });

  it("returns createdAt timestamp in ISO format", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Timestamp task",
      authorization: ws.bearerToken,
    });

    const beforeTime = new Date();
    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
    });
    const afterTime = new Date();

    expect(record.createdAt).toBeDefined();
    expect(typeof record.createdAt).toBe("string");
    expect(record.createdAt).toMatch(/^\d{4}-\d{2}-\d{2}T/); // ISO format
    const recordTime = new Date(record.createdAt);
    expect(recordTime.getTime()).toBeGreaterThanOrEqual(beforeTime.getTime() - 100); // Allow 100ms buffer
    expect(recordTime.getTime()).toBeLessThanOrEqual(afterTime.getTime() + 100); // Allow 100ms buffer
  });

  it("converts bigint IDs to string in response", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "ID conversion task",
      authorization: ws.bearerToken,
    });

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
    });

    expect(typeof record.workspaceId).toBe("string");
    expect(typeof record.taskId).toBe("string");
    // decisionRecordId should be null when not provided
    expect(record.decisionRecordId).toBeNull();
  });

  it("handles null optional fields correctly", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Null fields task",
      authorization: ws.bearerToken,
    });

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
      runId: undefined,
      toolCallId: undefined,
      decisionRecordId: undefined,
      errorDetails: undefined,
    });

    expect(record.runId).toBeNull();
    expect(record.toolCallId).toBeNull();
    expect(record.decisionRecordId).toBeNull();
    expect(record.errorDetails).toBeNull();
  });

  it("records multiple executions for the same task", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Multi-execution task",
      authorization: ws.bearerToken,
    });

    const records: TaskExecutionRecordView[] = [];
    for (let i = 0; i < 3; i++) {
      const record = await recordTaskExecutionService({
        workspaceId: BigInt(ws.workspaceId),
        taskId: BigInt(task.id),
        capabilityId: `capability-${i}`,
        triggeredByKind: "system",
      });
      records.push(record);
    }

    // All records should reference the same task
    expect(records.every((r) => r.taskId === task.id)).toBe(true);

    // All records should have unique IDs
    const ids = records.map((r) => r.id);
    expect(new Set(ids).size).toBe(3);
  });

  it("preserves complex errorDetails objects", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Error details task",
      authorization: ws.bearerToken,
    });

    const errorDetails = {
      code: "EXECUTION_FAILED",
      message: "Task execution failed",
      context: {
        retryCount: 3,
        lastError: "Connection timeout",
        nested: {
          deep: "value",
        },
      },
    };

    const record = await recordTaskExecutionService({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      capabilityId: "test-capability",
      triggeredByKind: "system",
      status: "FAILED",
      errorDetails,
    });

    expect(record.errorDetails).toEqual(errorDetails);
  });

  it("stores execution records with workspace isolation", async () => {
    const ws1 = await createTestWorkspaceWithMember();
    const ws2 = await createTestWorkspaceWithMember();

    const task1 = await createTask({
      workspaceId: ws1.workspaceId,
      title: "Task in WS1",
      authorization: ws1.bearerToken,
    });

    const task2 = await createTask({
      workspaceId: ws2.workspaceId,
      title: "Task in WS2",
      authorization: ws2.bearerToken,
    });

    const record1 = await recordTaskExecutionService({
      workspaceId: BigInt(ws1.workspaceId),
      taskId: BigInt(task1.id),
      capabilityId: "capability-1",
      triggeredByKind: "system",
    });

    const record2 = await recordTaskExecutionService({
      workspaceId: BigInt(ws2.workspaceId),
      taskId: BigInt(task2.id),
      capabilityId: "capability-2",
      triggeredByKind: "system",
    });

    // Records should belong to their respective workspaces
    expect(record1.workspaceId).toBe(ws1.workspaceId);
    expect(record2.workspaceId).toBe(ws2.workspaceId);

    // And reference their respective tasks
    expect(record1.taskId).toBe(task1.id);
    expect(record2.taskId).toBe(task2.id);
  });

  it("supports all status and triggeredByKind combinations", async () => {
    const ws = await createTestWorkspaceWithMember();
    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Combination task",
      authorization: ws.bearerToken,
    });

    const statuses = ["SUCCESS", "FAILED"] as const;
    const kinds = ["agent", "founder", "workflow", "system"] as const;

    let count = 0;
    for (const status of statuses) {
      for (const kind of kinds) {
        const record = await recordTaskExecutionService({
          workspaceId: BigInt(ws.workspaceId),
          taskId: BigInt(task.id),
          capabilityId: `capability-${count}`,
          triggeredByKind: kind,
          status,
        });

        expect(record.status).toBe(status);
        expect(record.triggeredByKind).toBe(kind);
        count++;
      }
    }
  });
});
