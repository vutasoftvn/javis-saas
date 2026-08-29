import { describe, it, expect } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../identity/models/db";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("workspace-scoped project relations", () => {
  describe("task_projects composite FK", () => {
    it("rejects cross-workspace link: task in A + project in B", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "admin" });
      const wsB = await createSecondWorkspace();

      // Create task in workspace A
      const taskId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO operating.tasks (id, workspace_id, title, status, priority, timezone)
          VALUES (${taskId}, ${BigInt(wsA.workspaceId)}, 'Task in A', 'todo', 'medium', 'UTC')`
      );

      // Create project in workspace B
      const projectId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.projects (id, workspace_id, title, status)
          VALUES (${projectId}, ${BigInt(wsB.workspaceId)}, 'Project in B', 'ACTIVE')`
      );

      // Try to link task A to project B — should fail with FK constraint
      await expect(
        db.execute(
          sql`INSERT INTO operating.task_projects (workspace_id, task_id, project_id)
            VALUES (${BigInt(wsA.workspaceId)}, ${taskId}, ${projectId})`
        )
      ).rejects.toThrow();
    });

    it("accepts same-workspace links: two projects in A", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "admin" });

      // Create task in workspace A
      const taskId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO operating.tasks (id, workspace_id, title, status, priority, timezone)
          VALUES (${taskId}, ${BigInt(wsA.workspaceId)}, 'Task in A', 'todo', 'medium', 'UTC')`
      );

      // Create two projects in workspace A
      const projectId1 = generateSnowflake();
      const projectId2 = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.projects (id, workspace_id, title, status)
          VALUES (${projectId1}, ${BigInt(wsA.workspaceId)}, 'Project A1', 'ACTIVE')`
      );
      await db.execute(
        sql`INSERT INTO strategy.projects (id, workspace_id, title, status)
          VALUES (${projectId2}, ${BigInt(wsA.workspaceId)}, 'Project A2', 'ACTIVE')`
      );

      // Link task to both projects in same workspace — should succeed
      await db.execute(
        sql`INSERT INTO operating.task_projects (workspace_id, task_id, project_id)
          VALUES (${BigInt(wsA.workspaceId)}, ${taskId}, ${projectId1})`
      );

      await db.execute(
        sql`INSERT INTO operating.task_projects (workspace_id, task_id, project_id)
          VALUES (${BigInt(wsA.workspaceId)}, ${taskId}, ${projectId2})`
      );

      // Verify links exist
      const result = await db.execute(
        sql`SELECT task_id, project_id FROM operating.task_projects WHERE task_id = ${taskId}`
      );
      const links = (result as any).rows;
      expect(links).toHaveLength(2);
      const projectIds = links.map((l: any) => BigInt(l.project_id)).sort();
      expect(projectIds).toEqual([projectId1, projectId2].sort());
    });

    it("returns empty list for workspace-wide task with no links", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "admin" });

      // Create task in workspace A with no links
      const taskId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO operating.tasks (id, workspace_id, title, status, priority, timezone)
          VALUES (${taskId}, ${BigInt(wsA.workspaceId)}, 'Task with no links', 'todo', 'medium', 'UTC')`
      );

      // Query links — should return empty list
      const result = await db.execute(
        sql`SELECT task_id, project_id FROM operating.task_projects WHERE task_id = ${taskId}`
      );
      const links = (result as any).rows;
      expect(links).toHaveLength(0);
    });
  });

  describe("okr_objective_projects composite FK", () => {
    it("rejects cross-workspace link: objective in A + project in B", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "admin" });
      const wsB = await createSecondWorkspace();

      // Create cycle and objective in workspace A
      const cycleId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.okr_cycles (id, workspace_id, name, status)
          VALUES (${cycleId}, ${BigInt(wsA.workspaceId)}, 'Q1 A', 'draft')`
      );

      const objectiveId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.okr_objectives (id, workspace_id, cycle_id, title, status)
          VALUES (${objectiveId}, ${BigInt(wsA.workspaceId)}, ${cycleId}, 'Objective in A', 'draft')`
      );

      // Create project in workspace B
      const projectId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.projects (id, workspace_id, title, status)
          VALUES (${projectId}, ${BigInt(wsB.workspaceId)}, 'Project in B', 'ACTIVE')`
      );

      // Try to link objective A to project B — should fail with FK constraint
      await expect(
        db.execute(
          sql`INSERT INTO strategy.okr_objective_projects (workspace_id, objective_id, project_id)
            VALUES (${BigInt(wsA.workspaceId)}, ${objectiveId}, ${projectId})`
        )
      ).rejects.toThrow();
    });

    it("accepts same-workspace links: two projects in A", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "admin" });

      // Create cycle and objective in workspace A
      const cycleId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.okr_cycles (id, workspace_id, name, status)
          VALUES (${cycleId}, ${BigInt(wsA.workspaceId)}, 'Q1 A', 'draft')`
      );

      const objectiveId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.okr_objectives (id, workspace_id, cycle_id, title, status)
          VALUES (${objectiveId}, ${BigInt(wsA.workspaceId)}, ${cycleId}, 'Objective in A', 'draft')`
      );

      // Create two projects in workspace A
      const projectId1 = generateSnowflake();
      const projectId2 = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.projects (id, workspace_id, title, status)
          VALUES (${projectId1}, ${BigInt(wsA.workspaceId)}, 'Project A1', 'ACTIVE')`
      );
      await db.execute(
        sql`INSERT INTO strategy.projects (id, workspace_id, title, status)
          VALUES (${projectId2}, ${BigInt(wsA.workspaceId)}, 'Project A2', 'ACTIVE')`
      );

      // Link objective to both projects in same workspace — should succeed
      await db.execute(
        sql`INSERT INTO strategy.okr_objective_projects (workspace_id, objective_id, project_id)
          VALUES (${BigInt(wsA.workspaceId)}, ${objectiveId}, ${projectId1})`
      );

      await db.execute(
        sql`INSERT INTO strategy.okr_objective_projects (workspace_id, objective_id, project_id)
          VALUES (${BigInt(wsA.workspaceId)}, ${objectiveId}, ${projectId2})`
      );

      // Verify links exist
      const result = await db.execute(
        sql`SELECT objective_id, project_id FROM strategy.okr_objective_projects WHERE objective_id = ${objectiveId}`
      );
      const links = (result as any).rows;
      expect(links).toHaveLength(2);
      const projectIds = links.map((l: any) => BigInt(l.project_id)).sort();
      expect(projectIds).toEqual([projectId1, projectId2].sort());
    });

    it("returns empty list for objective with no links", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "admin" });

      // Create cycle and objective in workspace A with no links
      const cycleId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.okr_cycles (id, workspace_id, name, status)
          VALUES (${cycleId}, ${BigInt(wsA.workspaceId)}, 'Q1 A', 'draft')`
      );

      const objectiveId = generateSnowflake();
      await db.execute(
        sql`INSERT INTO strategy.okr_objectives (id, workspace_id, cycle_id, title, status)
          VALUES (${objectiveId}, ${BigInt(wsA.workspaceId)}, ${cycleId}, 'Objective with no links', 'draft')`
      );

      // Query links — should return empty list
      const result = await db.execute(
        sql`SELECT objective_id, project_id FROM strategy.okr_objective_projects WHERE objective_id = ${objectiveId}`
      );
      const links = (result as any).rows;
      expect(links).toHaveLength(0);
    });
  });
});
