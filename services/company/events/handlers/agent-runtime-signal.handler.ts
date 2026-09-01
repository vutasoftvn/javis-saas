import { api } from "encore.dev/api";
import {
  IngestAgentRuntimeSignalRequest,
  ingestAgentRuntimeSignalService,
} from "../services/agent-runtime-signal.service";

export type {
  AgentRuntimeSignalPayload,
  IngestAgentRuntimeSignalRequest,
} from "../services/agent-runtime-signal.service";

export { ingestAgentRuntimeSignalService };

export const ingestAgentRuntimeSignal = api(
  { method: "POST", expose: true, path: "/events/internal/agent-runtime-signal" },
  async (req: IngestAgentRuntimeSignalRequest): Promise<{ stored: boolean }> => {
    return ingestAgentRuntimeSignalService(req);
  }
);
