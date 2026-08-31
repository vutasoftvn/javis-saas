import { api, APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";
import {
  createE2eSession,
  type CreateE2eSessionParams,
  type E2eSession,
} from "../services/e2e-session.service";

export const createE2eSessionApi = api(
  { method: "POST", path: "/identity/_e2e/session", expose: false },
  async (params: CreateE2eSessionParams): Promise<E2eSession> => {
    if (isStagingOrProd()) {
      throw APIError.permissionDenied("E2E session endpoint is never available in staging/production");
    }
    if (process.env.E2E_TEST_SEED_ENABLED !== "1") {
      throw APIError.permissionDenied("E2E session endpoint disabled for this Company process");
    }
    return createE2eSession(params);
  }
);
