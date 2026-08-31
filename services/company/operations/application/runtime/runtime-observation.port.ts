import { RuntimeObservation } from "../../domain/runtime-observation";

export interface RuntimeObservationPort {
  latest(
    workspaceId: string,
    sourceKind: RuntimeObservation["sourceKind"]
  ): Promise<RuntimeObservation | null>;
}
