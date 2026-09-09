// COSA Automation MVP — internal outcome projection endpoint (Task 6).
// Authed by the worker service token; not a client-facing surface.

import { api } from "encore.dev/api";
import {
  projectAutomationOutcome,
  type ProjectAutomationOutcomeRequest,
  type ProjectAutomationOutcomeResult,
} from "../services/automation-outcome.service";

export const projectAutomationOutcomeEndpoint = api(
  { method: "POST", path: "/operations/automation/internal/outcome", expose: true },
  async (req: ProjectAutomationOutcomeRequest): Promise<ProjectAutomationOutcomeResult> => {
    return projectAutomationOutcome(req);
  }
);
