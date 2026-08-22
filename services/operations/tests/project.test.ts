import { describe, it, expect } from "vitest";
import { createProject, listProjects, createPortfolio, listPortfolios } from "../handlers/project.handler";

describe("Project & Portfolio Service", () => {
  const workspaceId = 200;

  it("creates a portfolio and lists it", async () => {
    const portfolio = await createPortfolio({
      workspaceId,
      name: "Core AI SaaS Suite",
      description: "Portfolio of main SaaS products",
      strategicFocus: "AI Agent OS",
    });

    expect(portfolio.id).toBeDefined();
    expect(portfolio.workspaceId).toBe(workspaceId);
    expect(portfolio.name).toBe("Core AI SaaS Suite");
    expect(portfolio.status).toBe("active");

    const list = await listPortfolios({ workspaceId });
    expect(list.portfolios.some((p) => p.id === portfolio.id)).toBe(true);
  });

  it("creates a project and lists it", async () => {
    const project = await createProject({
      workspaceId,
      title: "Realtime Voice Hologram",
      description: "Interactive voice agent for desktop",
      projectType: "PRODUCT",
      strategicPriority: "P0",
    });

    expect(project.id).toBeDefined();
    expect(project.workspaceId).toBe(workspaceId);
    expect(project.title).toBe("Realtime Voice Hologram");
    expect(project.status).toBe("active");

    const list = await listProjects({ workspaceId });
    expect(list.projects.some((p) => p.id === project.id)).toBe(true);
  });
});
