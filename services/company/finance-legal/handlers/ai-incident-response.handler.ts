import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  reportAiIncident,
  resolveAiIncident,
  type ReportAiIncidentInput,
  type ResolveAiIncidentInput,
} from "../services/ai-incident-response.service";

export interface ReportAiIncidentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  incidentType: string;
  summary: string;
  rootCause?: string;
  mitigation?: string;
}

export interface ResolveAiIncidentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  id: string;
  actionTaken: string;
  mitigation?: string;
}

export const reportAiIncidentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/incidents", expose: true },
  async (req: ReportAiIncidentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return reportAiIncident({
      ...req,
      workspaceId: ctx.workspaceId,
      reportedByMemberId: ctx.workforceMemberId || ctx.userId,
    });
  }
);

export const resolveAiIncidentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/incidents/:id/resolve", expose: true },
  async (req: ResolveAiIncidentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return resolveAiIncident({
      incidentId: req.id,
      resolvedByMemberId: ctx.workforceMemberId || ctx.userId,
      actionTaken: req.actionTaken,
      mitigation: req.mitigation,
    });
  }
);
