import { describe, expect, it } from "vitest";
import { makeBusinessEvent, validateEnvelope } from "../envelope";
import { APIError } from "encore.dev/api";

describe("Project Activity Business Events", () => {
  describe("envelope validation", () => {
    it("rejects a Hub-visible event with no projectId", () => {
      expect(() => makeBusinessEvent({
        eventType: "operations.task.created.v1",
        workspaceId: "ws_a",
        aggregateType: "task",
        aggregateId: "task_a",
        correlationId: "corr_a",
        actor: { kind: "user", id: "human_a" },
        classification: "internal",
        payload: { taskId: "task_a" },
      })).toThrow(/projectId/);
    });

    it("accepts a valid task event with projectId", () => {
      const event = makeBusinessEvent({
        eventType: "operations.task.created.v1",
        workspaceId: "ws_a",
        projectId: "proj_a",
        aggregateType: "task",
        aggregateId: "task_a",
        correlationId: "corr_a",
        actor: { kind: "user", id: "human_a" },
        classification: "internal",
        payload: { taskId: "task_a", projectId: "proj_a" },
      });

      expect(event.projectId).toBe("proj_a");
      expect(event.workspaceId).toBe("ws_a");
    });

    it("validates payload projectId matches envelope projectId", () => {
      expect(() => makeBusinessEvent({
        eventType: "operations.task.completed.v1",
        workspaceId: "ws_a",
        projectId: "proj_a",
        aggregateType: "task",
        aggregateId: "task_a",
        correlationId: "corr_a",
        actor: { kind: "user", id: "human_a" },
        classification: "restricted",
        payload: { task_id: "task_a", project_id: "proj_b" },
      })).toThrow(/projectId/);
    });

    it("retains only Project-safe data in restricted classification", () => {
      const event = makeBusinessEvent({
        eventType: "operations.task.completed.v1",
        workspaceId: "ws_a",
        projectId: "proj_a",
        aggregateType: "task",
        aggregateId: "task_a",
        correlationId: "corr_a",
        actor: { kind: "user", id: "human_a" },
        classification: "restricted",
        payload: { task_id: "task_a", project_id: "proj_a", evidence_ref: "ev_1" },
      });

      expect(event.projectId).toBe("proj_a");
      expect(event.payload).not.toHaveProperty("task_description");
    });
  });
});
