import { describe, expect, it, beforeEach } from "vitest";
import {
  onboardChannelConnector,
  setCustomOnboardingRunner,
} from "../../services/customer-engagement/channel-onboarding";

describe("Channel Connector Onboarding Helper Tests", () => {
  beforeEach(() => {
    setCustomOnboardingRunner(null);
  });

  it("should call control plane install, authorize and grant endpoints", async () => {
    const calls: string[] = [];
    setCustomOnboardingRunner(async (action, payload) => {
      calls.push(action);
      if (action === "install") {
        return { id: "inst_100", workspaceId: payload.workspaceId, connectorKey: payload.connectorKey };
      }
      if (action === "authorize") {
        return { id: "auth_200", installationId: payload.installationId };
      }
      if (action === "grant") {
        return { id: "grant_300", authorizationId: payload.authorizationId };
      }
      return {};
    });

    const res = await onboardChannelConnector(
      {
        workspaceId: "ws_test_99",
        connectorKey: "zalo_oa_key",
        secretRef: "sec_zalo_vault_1",
      },
      "Bearer test_token"
    );

    expect(res.installationId).toBe("inst_100");
    expect(res.authorizationId).toBe("auth_200");
    expect(calls).toEqual(["install", "authorize", "grant"]);
  });
});
