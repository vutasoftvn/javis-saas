import { createHmac } from "node:crypto";
import { claimDueOutboxEvents, completeOutboxEvent, failOutboxEvent } from "../shared/events/outbox.repository";
import { requireLocalServiceSecret } from "../shared/events/service-identity";

const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);

export function assertLocalTarget(url: string): void {
  const host = new URL(url).hostname;
  if (!LOCAL_HOSTS.has(host) && !host.endsWith(".local")) {
    throw new Error(`relay target must be local (Workspace Runtime Node), got ${host}`);
  }
}

export interface RelayDeps {
  post: (url: string, body: string, headers: Record<string, string>) => Promise<{ status: number; body: any }>;
  batchLimit: number;
  agentOsUrl: string;
}

export async function runRelayOnce(deps: RelayDeps): Promise<void> {
  assertLocalTarget(deps.agentOsUrl);
  const rows = await claimDueOutboxEvents("company-relay", deps.batchLimit);
  const secret = requireLocalServiceSecret();
  for (const row of rows) {
    const payload = JSON.stringify(row.envelope);
    const sig = createHmac("sha256", secret).update(payload).digest("hex");
    try {
      // Gửi đúng chuỗi đã ký (payload), không phải object — HMAC phải khớp byte-for-byte với intake.
      const res = await deps.post(`${deps.agentOsUrl}/agent/internal/events`, payload, {
        "X-COSA-Local-Signature": sig,
        "Content-Type": "application/json",
      });
      const outcome = res.body?.outcome;
      if (res.status === 200 && ["accepted", "duplicate", "ignored_rule_disabled"].includes(outcome)) {
        await completeOutboxEvent(row.eventId, row.claimToken!);
      } else if (res.status === 200 && outcome === "policy_denied") {
        await completeOutboxEvent(row.eventId, row.claimToken!); // terminal — không retry vô hạn
      } else {
        await failOutboxEvent(row.eventId, row.claimToken!, `status=${res.status} body=${JSON.stringify(res.body)}`);
      }
    } catch (e) {
      await failOutboxEvent(row.eventId, row.claimToken!, String(e));
    }
  }
}

export async function relayTick(): Promise<void> {
  await runRelayOnce({
    post: async (url, body, headers) => {
      // body đã là chuỗi JSON đã ký — gửi verbatim, không JSON.stringify lần nữa.
      const r = await fetch(url, { method: "POST", body, headers });
      return { status: r.status, body: await r.json().catch(() => ({})) };
    },
    batchLimit: Number(process.env.COSA_RELAY_BATCH_LIMIT || 50),
    agentOsUrl: process.env.COSA_AGENTOS_INTAKE_URL || "http://127.0.0.1:8000",
  });
}
