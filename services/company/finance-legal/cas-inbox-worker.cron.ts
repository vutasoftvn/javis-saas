// F3 — worker định kỳ claim cas_sync_inbox (nguồn 'webhook' VÀ 'poll' —
// cùng 1 hộp thư hợp nhất) và xử lý theo lease/backoff/DLQ. Đây là lưới an
// toàn cho mọi dòng chưa PROCESSED: webhook chỉ ACK nhanh (không xử lý
// inline), và GET-poll tự drain phần lớn ngay trong syncCasConnection —
// worker này nhặt lại phần còn sót (crash, lỗi tạm thời, backlog).
import { CronJob } from "encore.dev/cron";
import { api } from "encore.dev/api";
import { processCasInboxBatch } from "./services/cas-inbox-worker.service";

export const casInboxWorkerTickEndpoint = api(
  { method: "POST", expose: false, path: "/finance-legal/cas/inbox-worker/tick" },
  async (): Promise<void> => {
    await processCasInboxBatch({ limit: Number(process.env.CAS_INBOX_WORKER_BATCH_LIMIT || 50) });
  }
);

const _ = new CronJob("cas-inbox-worker", {
  title: "Cas.so ingestion inbox worker tick",
  every: "1m",
  endpoint: casInboxWorkerTickEndpoint,
});
