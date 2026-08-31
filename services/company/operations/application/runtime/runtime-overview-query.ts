import { RuntimeObservationPort } from "./runtime-observation.port";
import { RuntimeSignalProjector, ProjectedSourceStatus } from "./runtime-signal-projector";
import { DrizzleRuntimeObservationRepository } from "../../infrastructure/runtime/drizzle-runtime-observation.repository";

export class RuntimeOverviewQuery {
  constructor(
    private readonly repo: RuntimeObservationPort = new DrizzleRuntimeObservationRepository()
  ) {}

  async getSourceStatuses(workspaceId: string): Promise<readonly ProjectedSourceStatus[]> {
    const companyObs = await this.repo.latest(workspaceId, "company");
    const agentObs = await this.repo.latest(workspaceId, "agent");

    const results: ProjectedSourceStatus[] = [];
    if (companyObs) {
      results.push(RuntimeSignalProjector.toSourceStatus(companyObs));
    }
    if (agentObs) {
      results.push(RuntimeSignalProjector.toSourceStatus(agentObs));
    }

    return results;
  }
}
