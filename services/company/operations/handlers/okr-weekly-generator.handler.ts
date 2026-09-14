// services/company/operations/handlers/okr-weekly-generator.handler.ts
//
// Endpoint mỏng: parse input → requireWorkspaceAccess → gọi service →
// trả CycleDto. Không import drizzle/db/schema trực tiếp (Encore Handler
// Boundary).
import { api, Header, APIError } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateCycleFromObjective } from "../services/okr-weekly-generator.service";
import { CycleDto } from "../services/project-operating-loop.service";

interface GenerateWeeklyCycleParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  durationWeeks: number;
}

export const generateWeeklyCycleFromObjective = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/objectives/:objectiveId/generate-weekly-cycle",
  },
  async (params: GenerateWeeklyCycleParams): Promise<CycleDto> => {
    if (params.durationWeeks < 1 || params.durationWeeks > 12) {
      throw APIError.invalidArgument("durationWeeks must be between 1 and 12");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return generateCycleFromObjective(ctx, params.objectiveId, params.durationWeeks);
  }
);
