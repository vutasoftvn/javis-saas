import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  ENGAGEMENT_PERMISSIONS,
  requireEngagementPermission,
} from "../../services/customer-engagement/rbac";
import {
  createOrVersionRule,
  enableRule,
  disableRule,
  listRules,
} from "../../services/customer-engagement/automation/rule-store.service";
import { evaluateRules } from "../../services/customer-engagement/automation/evaluator";
import * as applicationsSvc from "../../services/customer-engagement/automation/applications.service";

export interface CreateRuleParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  ruleKey: string;
  name: string;
  trigger: "thread_opened" | "message_received" | "thread_status_changed" | "csat_recorded" | "time_sweep";
  priority?: number;
  condition: any;
  actions: any[];
  enabled?: boolean;
  stopOnMatch?: boolean;
  effectiveFrom?: string;
  effectiveUntil?: string;
}

export interface RuleKeyParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  key: string;
}

export interface ListRulesParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
}

export interface DryRunParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  id: string;
  trigger: string;
}

export interface ListThreadApplicationsParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  id: string;
}

export const createOrVersionRuleApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/automation/rules" },
  async (params: CreateRuleParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOMATION_MANAGE);

    return createOrVersionRule(
      {
        ruleKey: params.ruleKey,
        name: params.name,
        trigger: params.trigger,
        priority: params.priority ?? 100,
        condition: params.condition,
        actions: params.actions,
        enabled: params.enabled,
        stopOnMatch: params.stopOnMatch ?? false,
        effectiveFrom: params.effectiveFrom ? new Date(params.effectiveFrom) : undefined,
        effectiveUntil: params.effectiveUntil ? new Date(params.effectiveUntil) : null,
      },
      ctx
    );
  }
);

export const enableRuleApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/automation/rules/:key/enable" },
  async (params: RuleKeyParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOMATION_MANAGE);

    return enableRule(params.key, ctx);
  }
);

export const disableRuleApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/automation/rules/:key/disable" },
  async (params: RuleKeyParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOMATION_MANAGE);

    return disableRule(params.key, ctx);
  }
);

export const listRulesApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/automation/rules" },
  async (params: ListRulesParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOMATION_MANAGE);

    const rules = await listRules(ctx);
    return { rules };
  }
);

export const dryRunAutomationApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/automation/dry-run" },
  async (params: DryRunParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOMATION_MANAGE);

    const res = await evaluateRules(
      {
        trigger: params.trigger,
        threadId: params.id,
        dryRun: true,
      },
      ctx
    );

    return {
      facts: res.facts,
      matched: res.matched,
    };
  }
);

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
