import { describe, it, expect } from "vitest";
import { buildTaskCreatedEvent, buildTaskCompletedEvent, EventContext } from "../services/task-events.service";
import { createTask } from "../handlers/task.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { Task } from "../handlers/task.handler";

describe("Task Events Service", () => {
  describe("buildTaskCreatedEvent", () => {
    it("builds a task created event with default system actor and generated correlationId", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Test task",
        authorization: ws.bearerToken,
      });

      // Cast to required Task type (the service expects task.id and task.workspaceId as strings)
      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const event = buildTaskCreatedEvent(taskData);

      expect(event).toBeDefined();
      expect(event.eventType).toBe("operations.task.created.v1");
      expect(event.workspaceId).toBe(task.workspaceId);
      expect(event.aggregateType).toBe("task");
      expect(event.aggregateId).toBe(task.id);
      expect(event.correlationId).toBeDefined();
      expect(event.correlationId).toMatch(/^[0-9a-f-]{36}$/); // UUID format
      expect(event.actor).toEqual({ kind: "system", id: "operations" });
      expect(event.payload).toEqual({
        taskId: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
      });
    });

    it("uses provided correlationId from context", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Test task",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const providedCorrelationId = "my-correlation-123";
      const ctx: EventContext = { correlationId: providedCorrelationId };

      const event = buildTaskCreatedEvent(taskData, ctx);

      expect(event.correlationId).toBe(providedCorrelationId);
    });

    it("uses provided causationId from context", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Test task",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const providedCausationId = "caused-by-456";
      const ctx: EventContext = { causationId: providedCausationId };

      const event = buildTaskCreatedEvent(taskData, ctx);

      expect(event.causationId).toBe(providedCausationId);
    });

    it("uses provided actor from context", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Test task",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const ctx: EventContext = {
        actor: { kind: "user", id: "user-789" },
      };

      const event = buildTaskCreatedEvent(taskData, ctx);

      expect(event.actor).toEqual({ kind: "user", id: "user-789" });
    });

    it("supports agent actor kind", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Agent created",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const ctx: EventContext = {
        actor: { kind: "agent", id: "agent-xyz" },
      };

      const event = buildTaskCreatedEvent(taskData, ctx);

      expect(event.actor).toEqual({ kind: "agent", id: "agent-xyz" });
    });

    it("includes all task fields in payload", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Detailed task",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const event = buildTaskCreatedEvent(taskData);

      expect(event.payload).toMatchObject({
        taskId: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
      });
    });

    it("classification is internal", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Test task",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const event = buildTaskCreatedEvent(taskData);

      expect(event.classification).toBe("internal");
    });
  });

  describe("buildTaskCompletedEvent", () => {
    it("builds a task completed event with default system actor", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Task to complete",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const event = buildTaskCompletedEvent(taskData);

      expect(event).toBeDefined();
      expect(event.eventType).toBe("operations.task.completed.v1");
      expect(event.workspaceId).toBe(task.workspaceId);
      expect(event.aggregateType).toBe("task");
      expect(event.aggregateId).toBe(task.id);
      expect(event.correlationId).toBeDefined();
      expect(event.actor).toEqual({ kind: "system", id: "operations" });
    });

    it("includes completedAt timestamp in payload", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Task to complete",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const event = buildTaskCompletedEvent(taskData);

      expect(event.payload).toMatchObject({
        taskId: task.id,
        workspaceId: task.workspaceId,
      });
      expect(event.payload.completedAt).toBeDefined();
      expect(event.payload.completedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/); // ISO format
      // Verify it's a valid ISO timestamp string
      expect(() => new Date(event.payload.completedAt)).not.toThrow();
    });

    it("uses provided correlationId from context", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Task to complete",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const providedCorrelationId = "complete-correlation-123";
      const ctx: EventContext = { correlationId: providedCorrelationId };

      const event = buildTaskCompletedEvent(taskData, ctx);

      expect(event.correlationId).toBe(providedCorrelationId);
    });

    it("uses provided causationId from context", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Task to complete",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const providedCausationId = "caused-complete-456";
      const ctx: EventContext = { causationId: providedCausationId };

      const event = buildTaskCompletedEvent(taskData, ctx);

      expect(event.causationId).toBe(providedCausationId);
    });

    it("uses provided actor from context", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Task to complete",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const ctx: EventContext = {
        actor: { kind: "user", id: "user-complete-789" },
      };

      const event = buildTaskCompletedEvent(taskData, ctx);

      expect(event.actor).toEqual({ kind: "user", id: "user-complete-789" });
    });

    it("classification is internal for completed events", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Task to complete",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const event = buildTaskCompletedEvent(taskData);

      expect(event.classification).toBe("internal");
    });

    it("both events maintain consistent schema structure", async () => {
      const ws = await createTestWorkspaceWithMember();
      const task = await createTask({
        workspaceId: ws.workspaceId,
        title: "Schema test",
        authorization: ws.bearerToken,
      });

      const taskData: Task = {
        id: task.id,
        workspaceId: task.workspaceId,
        title: task.title,
        status: task.status,
        priority: task.priority || "medium",
        timezone: task.timezone || "UTC",
      } as Task;

      const createdEvent = buildTaskCreatedEvent(taskData);
      const completedEvent = buildTaskCompletedEvent(taskData);

      // Both should have the same basic envelope structure
      expect(createdEvent).toHaveProperty("eventType");
      expect(createdEvent).toHaveProperty("workspaceId");
      expect(createdEvent).toHaveProperty("aggregateType");
      expect(createdEvent).toHaveProperty("aggregateId");
      expect(createdEvent).toHaveProperty("correlationId");
      expect(createdEvent).toHaveProperty("actor");
      expect(createdEvent).toHaveProperty("classification");
      expect(createdEvent).toHaveProperty("payload");

      expect(completedEvent).toHaveProperty("eventType");
      expect(completedEvent).toHaveProperty("workspaceId");
      expect(completedEvent).toHaveProperty("aggregateType");
      expect(completedEvent).toHaveProperty("aggregateId");
      expect(completedEvent).toHaveProperty("correlationId");
      expect(completedEvent).toHaveProperty("actor");
      expect(completedEvent).toHaveProperty("classification");
      expect(completedEvent).toHaveProperty("payload");

      // Same aggregates
      expect(createdEvent.aggregateType).toBe(completedEvent.aggregateType);
      expect(createdEvent.aggregateId).toBe(completedEvent.aggregateId);
      expect(createdEvent.workspaceId).toBe(completedEvent.workspaceId);
    });
  });
});
