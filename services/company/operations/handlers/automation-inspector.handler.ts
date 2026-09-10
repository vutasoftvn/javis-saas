// COSA Automation MVP — Run Inspector + Needs You endpoints (Task 8).

import { api, Header } from "encore.dev/api";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  getAutomationRunInspector,
  listAutomationNeedsYou,
  type AutomationRunInspectorView,
  type NeedsYouItemView,
} from "../services/automation-inspector.service";

interface WsHeaders {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getAutomationRunInspectorEndpoint = api(
  { method: "GET", path: "/operations/automation/invocations/:invocationId/inspector", expose: true },
  async (
    params: WsHeaders & { invocationId: string }
  ): Promise<MvpSuccess<AutomationRunInspectorView>> => {
    return getAutomationRunInspector(params);
  }
);

export const listAutomationNeedsYouEndpoint = api(
  { method: "GET", path: "/operations/automation/needs-you", expose: true },
  async (params: WsHeaders): Promise<MvpSuccess<readonly NeedsYouItemView[]>> => {
    return listAutomationNeedsYou(params);
  }
);
