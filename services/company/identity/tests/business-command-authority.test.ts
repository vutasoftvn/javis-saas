import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { requireFounderCommand } from "../services/command-authority.service";

describe("business-command-authority", () => {
  it("auditor cannot manage agent policy", () => {
    expect(() =>
      requireFounderCommand(
        {
          workspaceId: "101",
          userId: "201",
          workforceMemberId: "301",
          membershipRole: "auditor",
          permissions: ["read"],
          correlationId: "audit-1",
        },
        "agent.policy.manage"
      )
    ).toThrow(APIError);
  });

  it("member cannot approve execution plan", () => {
    expect(() =>
      requireFounderCommand(
        {
          workspaceId: "101",
          userId: "202",
          workforceMemberId: "302",
          membershipRole: "member",
          permissions: ["read"],
          correlationId: "audit-2",
        },
        "execution.plan.approve"
      )
    ).toThrow(APIError);
  });

  it("founder can execute commands", () => {
    expect(() =>
      requireFounderCommand(
        {
          workspaceId: "101",
          userId: "203",
          workforceMemberId: "303",
          membershipRole: "founder",
          permissions: ["*"],
          correlationId: "audit-3",
        },
        "agent.policy.manage"
      )
    ).not.toThrow();
  });

  it("co-founder can execute commands", () => {
    expect(() =>
      requireFounderCommand(
        {
          workspaceId: "101",
          userId: "204",
          workforceMemberId: "304",
          membershipRole: "co-founder",
          permissions: ["*"],
          correlationId: "audit-4",
        },
        "ai.deployment.approve"
      )
    ).not.toThrow();
  });
});
