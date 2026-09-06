// F3 — tick định kỳ GET-poll cho các bank_connections đến hạn (chưa từng
// sync hoặc quá interval từ lần sync thành công gần nhất). Đây là "cạnh
// không tinh khiết" (impure edge) của cas-sync.service.ts: cas-sync.service
// nhận `getTransactions` qua dependency injection để test được không cần
// mạng thật (giống pattern services/company/events/outbox-relay.service.ts);
// file này mới thực sự nối vào cas-client.ts + resolve access token.
import { CronJob } from "encore.dev/cron";
import { api, APIError } from "encore.dev/api";
import { casGetTransactions } from "./services/cas-client";
import { runCasSyncTick, type ConnectionRef } from "./services/cas-sync.service";

/**
 * TODO (theo dõi ở F2 follow-up): chưa có tích hợp secret vault thật cho
 * access token Cas.so — exchangeCasTokenService hiện tại (F2) cũng chỉ lưu
 * secretRef mock, chưa gọi casExchangePublicToken thật để có token thật.
 * Fail-closed rõ ràng ở đây thay vì giả vờ một resolver hoạt động: set env
 * CAS_ACCESS_TOKEN_<connectionId> để test/vận hành tạm, hoặc thay hàm này khi
 * secret vault thật sẵn sàng.
 */
async function resolveCasAccessToken(connectionId: string): Promise<string> {
  const envKey = `CAS_ACCESS_TOKEN_${connectionId}`;
  const token = process.env[envKey];
  if (!token) {
    throw APIError.failedPrecondition(
      `CAS_ACCESS_TOKEN_RESOLUTION_NOT_CONFIGURED: no access token resolvable for connection ${connectionId} (set ${envKey}, or wire a real secret vault resolver before enabling GET-poll in production)`
    );
  }
  return token;
}

export const casSyncTickEndpoint = api(
  { method: "POST", expose: false, path: "/finance-legal/cas/sync/tick" },
  async (): Promise<void> => {
    await runCasSyncTick({
      getTransactions: async (connection: ConnectionRef, opts) => {
        const accessToken = await resolveCasAccessToken(connection.id);
        const clientId = process.env.CAS_CLIENT_ID ?? "";
        const secretKey = process.env.CAS_SECRET_KEY ?? "";
        if (!clientId || !secretKey) {
          throw APIError.failedPrecondition(
            "CAS_CREDENTIALS_MISSING: CAS_CLIENT_ID, CAS_SECRET_KEY must be configured"
          );
        }
        return casGetTransactions(
          {
            accessToken,
            environment: connection.providerEnvironment as "sandbox" | "production",
            clientId,
            secretKey,
          },
          opts
        );
      },
    });
  }
);

const _ = new CronJob("cas-sync", {
  title: "Cas.so GET-poll incremental sync tick",
  every: "15m",
  endpoint: casSyncTickEndpoint,
});
