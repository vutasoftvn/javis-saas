import { MAX_ENQUEUE_BACKOFF_SEC } from "./schedule-types";

/**
 * Exponential backoff cho retry enqueue: lần thất bại đầu tiên retry ngay ở
 * tick kế tiếp (0s — hầu hết lỗi enqueue là transient, giữ dispatcher phản
 * hồi nhanh), từ lần thất bại thứ 2 trở đi mới giãn cách 5s, 10s, 20s, ...
 * cap 5 phút để tránh dồn tải khi lỗi kéo dài (vd. hạ tầng đang down).
 */
export function computeEnqueueBackoffSeconds(attemptCount: number): number {
  if (attemptCount <= 1) return 0;
  return Math.min(5 * 2 ** (attemptCount - 2), MAX_ENQUEUE_BACKOFF_SEC);
}

/**
 * Ghi log có cấu trúc (JSON) làm metric thay thế correlation fields
 * (execution id, attempt, next attempt, queue age) để dashboard log-based
 * query được mà không cần thêm dependency mới.
 */
export function logEnqueueRetryMetric(fields: {
  event: "enqueue_retry_scheduled" | "enqueue_failed_terminal";
  executionId: string;
  definitionId: string;
  attemptCount: number;
  maxAttempts: number;
  nextAttemptAt: Date | null;
  queueAgeMs: number;
  error: string;
}): void {
  console.warn(
    `[ScheduleDispatcher] metric=${JSON.stringify({
      ...fields,
      nextAttemptAt: fields.nextAttemptAt?.toISOString() ?? null,
    })}`
  );
}
