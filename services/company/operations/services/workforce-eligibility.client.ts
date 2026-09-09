import { APIError } from "encore.dev/api";

/**
 * Client gọi Agent Platform (apps/cosa) để lấy "facts" eligibility của một AI
 * employee TRƯỚC khi Company tạo/reassign attempt (spec §4, Task 3). Trả về
 * facts — KHÔNG runtime credential. Fail closed: timeout / foreign employee /
 * thiếu capability / status không ACTIVE => ném 409/503, không tạo attempt.
 */

export interface EligibilityQuery {
  workspaceId: string;
  agentInstanceId: string;
  assignmentId?: string;
  requiredCapabilityRefs: string[];
  correlationId?: string;
}

export interface EligibilityFacts {
  agentInstanceId: string;
  assignmentId: string;
  status: "ACTIVE" | "SUSPENDED" | "RETIRED";
  specSnapshot: { specId: string; specVersion: string; definitionHash: string };
  capabilityRefs: string[];
  capacityAvailable: boolean;
}

export type EligibilityTransport = (
  query: EligibilityQuery
) => Promise<{ status: number; body: unknown }>;

const CONTROL_PLANE_TIMEOUT_MS = 5000;

function getControlPlaneUrl(): string {
  return (
    process.env.COSA_AGENTOS_INTAKE_URL ||
    process.env.PLATFORM_API_BASE_URL ||
    "http://127.0.0.1:8000"
  );
}

function requireWorkforceAuthzToken(): string {
  // Secret riêng, single-purpose — KHÔNG tái dùng browser token / worker secret.
  const token = process.env.COSA_WORKFORCE_AUTHZ_SERVICE_TOKEN;
  if (!token) {
    // Dev fallback rõ ràng; staging/prod phải set (kiểm ở deploy-preflight).
    return "dev-workforce-authz-token";
  }
  return token;
}

const defaultTransport: EligibilityTransport = async (query) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CONTROL_PLANE_TIMEOUT_MS);
  try {
    const res = await fetch(`${getControlPlaneUrl()}/agent/internal/workforce/eligibility`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Workforce-Authz-Token": requireWorkforceAuthzToken(),
      },
      body: JSON.stringify({
        workspace_id: query.workspaceId,
        agent_instance_id: query.agentInstanceId,
        assignment_id: query.assignmentId ?? null,
        required_capability_refs: query.requiredCapabilityRefs,
        correlation_id: query.correlationId ?? null,
      }),
    });
    return { status: res.status, body: await res.json().catch(() => ({})) };
  } finally {
    clearTimeout(timer);
  }
};

let transport: EligibilityTransport = defaultTransport;

/** Test-only: thay transport mặc định. */
export function setEligibilityTransport(t: EligibilityTransport | null): void {
  transport = t ?? defaultTransport;
}

function parseFacts(body: unknown): EligibilityFacts {
  const b = (body ?? {}) as Record<string, unknown>;
  const data = (b.data ?? b) as Record<string, unknown>;
  const spec = (data.spec_snapshot ?? data.specSnapshot ?? {}) as Record<string, unknown>;
  return {
    agentInstanceId: String(data.agent_instance_id ?? data.agentInstanceId ?? ""),
    assignmentId: String(data.assignment_id ?? data.assignmentId ?? ""),
    status: String(data.status ?? "") as EligibilityFacts["status"],
    specSnapshot: {
      specId: String(spec.spec_id ?? spec.specId ?? ""),
      specVersion: String(spec.spec_version ?? spec.specVersion ?? ""),
      definitionHash: String(spec.definition_hash ?? spec.definitionHash ?? ""),
    },
    capabilityRefs: Array.isArray(data.capability_refs ?? data.capabilityRefs)
      ? ((data.capability_refs ?? data.capabilityRefs) as string[]).map(String)
      : [],
    capacityAvailable: Boolean(data.capacity_available ?? data.capacityAvailable ?? false),
  };
}

/**
 * Kiểm tra eligibility, ném lỗi typed nếu không đủ điều kiện. Không side-effect.
 */
export async function assertEmployeeEligible(query: EligibilityQuery): Promise<EligibilityFacts> {
  if (!query.agentInstanceId?.trim()) {
    throw APIError.invalidArgument("agentInstanceId is required for eligibility check");
  }

  let res: { status: number; body: unknown };
  try {
    res = await transport(query);
  } catch (e) {
    // Timeout / network — 503, không tạo attempt.
    throw APIError.unavailable(`workforce eligibility lookup failed: ${String(e)}`);
  }

  if (res.status === 404) {
    throw APIError.aborted("workforce employee not found in this workspace (foreign or unknown)");
  }
  if (res.status >= 500) {
    throw APIError.unavailable(`workforce eligibility lookup returned ${res.status}`);
  }
  if (res.status !== 200) {
    throw APIError.aborted(`workforce eligibility lookup rejected with ${res.status}`);
  }

  const facts = parseFacts(res.body);

  if (facts.agentInstanceId !== query.agentInstanceId) {
    throw APIError.aborted("eligibility facts do not match the requested employee");
  }
  if (facts.status !== "ACTIVE") {
    throw APIError.aborted(`workforce employee is ${facts.status}, not ACTIVE`);
  }
  if (query.assignmentId && facts.assignmentId !== query.assignmentId) {
    throw APIError.aborted("assignment mismatch for workforce employee");
  }
  const missing = query.requiredCapabilityRefs.filter(
    (c) => !facts.capabilityRefs.includes(c)
  );
  if (missing.length > 0) {
    throw APIError.aborted(`workforce employee missing capabilities: ${missing.join(", ")}`);
  }
  if (!facts.capacityAvailable) {
    throw APIError.aborted("workforce employee has no available capacity");
  }

  return facts;
}
