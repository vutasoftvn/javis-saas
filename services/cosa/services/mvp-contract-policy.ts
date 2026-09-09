// Adapter: đọc metadata contract MVP đã sinh (nguồn: shared/contracts/
// mvp-surface.json) MỘT LẦN lúc khởi động và cung cấp cho surface policy của
// Control Plane. KHÔNG đọc JSON trên mỗi HTTP request.
//
// Founder Trial R1 — mọi surface AVAILABLE/PILOT/CONFIGURATION_REQUIRED phải
// tham chiếu tới capability id đang enabled trong contract; chỉ PLANNED mới có
// contractEndpoint = null.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { SurfacePolicyEntry } from "./surface-policy";

interface RawCapability {
  id: string;
  enabled: boolean;
}

interface RawContract {
  version: string;
  capabilities: RawCapability[];
}

const CONTRACT_PATH = fileURLToPath(
  new URL("../../../shared/contracts/mvp-surface.json", import.meta.url)
);

let cached: { version: string; enabledIds: ReadonlySet<string> } | null = null;

function loadContract(): { version: string; enabledIds: ReadonlySet<string> } {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(CONTRACT_PATH, "utf8")) as RawContract;
  const enabledIds = new Set(
    raw.capabilities.filter((c) => c.enabled).map((c) => c.id)
  );
  cached = { version: raw.version, enabledIds };
  return cached;
}

export function loadEnabledMvpCapabilityIds(): ReadonlySet<string> {
  return loadContract().enabledIds;
}

export function mvpContractVersion(): string {
  return loadContract().version;
}

type ContractInput =
  | ReadonlySet<string>
  | { capabilities: Array<{ id: string; enabled?: boolean }> };

function toEnabledIdSet(contract: ContractInput): ReadonlySet<string> {
  if (contract instanceof Set) return contract;
  const caps = (contract as { capabilities: Array<{ id: string; enabled?: boolean }> })
    .capabilities;
  return new Set(caps.filter((c) => c.enabled !== false).map((c) => c.id));
}

const LIVE_STATUSES: ReadonlySet<string> = new Set([
  "AVAILABLE",
  "PILOT",
  "CONFIGURATION_REQUIRED",
]);

/**
 * Ném lỗi nếu surface policy lệch contract MVP:
 *  - surface live (AVAILABLE/PILOT/CONFIGURATION_REQUIRED) PHẢI có
 *    `requiredCapabilities` không rỗng, mọi id nằm trong contract enabled, và
 *    `contractEndpoint` không null + cũng nằm trong contract enabled;
 *  - surface PLANNED PHẢI có `contractEndpoint === null`.
 */
export function validateSurfacePolicyAgainstMvpContract(
  policy: readonly SurfacePolicyEntry[],
  contract: ContractInput
): void {
  const enabled = toEnabledIdSet(contract);
  const errors: string[] = [];

  for (const entry of policy) {
    if (LIVE_STATUSES.has(entry.defaultStatus)) {
      if (entry.requiredCapabilities.length === 0) {
        errors.push(
          `${entry.surfaceKey}: live surface (${entry.defaultStatus}) must declare non-empty requiredCapabilities`
        );
      }
      for (const cap of entry.requiredCapabilities) {
        if (!enabled.has(cap)) {
          errors.push(
            `${entry.surfaceKey}: requiredCapabilities entry '${cap}' is not an enabled MVP contract capability`
          );
        }
      }
      if (entry.contractEndpoint == null) {
        errors.push(
          `${entry.surfaceKey}: live surface must set contractEndpoint to an enabled contract capability`
        );
      } else if (!enabled.has(entry.contractEndpoint)) {
        errors.push(
          `${entry.surfaceKey}: contractEndpoint '${entry.contractEndpoint}' is not an enabled MVP contract capability`
        );
      }
    } else if (entry.defaultStatus === "PLANNED") {
      if (entry.contractEndpoint != null) {
        errors.push(
          `${entry.surfaceKey}: PLANNED surface must have a null contractEndpoint`
        );
      }
    }
  }

  if (errors.length > 0) {
    throw new Error(
      "Surface policy is out of sync with the MVP contract:\n  " +
        errors.join("\n  ")
    );
  }
}
