import { api } from "encore.dev/api";
import { ingestInbound } from "../../../services/customer-engagement/channel-inbound.service";

// Raw webhook handler for Zalo OA
export const zaloWebhookApi = api.raw(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/zalo/webhook" },
  async (req, resp) => {
    try {
      const chunks: Buffer[] = [];
      for await (const chunk of req) {
        chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
      }
      const rawBody = Buffer.concat(chunks);
      const headers = (req.headers || {}) as Record<string, string | undefined>;

      const result = await ingestInbound("zalo", { rawBody, headers });

      resp.statusCode = result.status;
      resp.setHeader("Content-Type", "application/json");
      resp.end(JSON.stringify(result));
    } catch (err: any) {
      resp.statusCode = 500;
      resp.setHeader("Content-Type", "application/json");
      resp.end(JSON.stringify({ error: err.message || "Internal server error" }));
    }
  }
);
