// Task 2 (B1) / ADR-FOUNDER-CHANNEL-001 — adapter Telegram Bot API cho kênh
// nhận thông báo của founder. Đặt sau interface `FounderChannelAdapter` để
// tiêm được test double (không gọi mạng thật trong test), cùng mẫu
// `setCustomChannelSecretResolver` ở
// `services/company/commercial/services/customer-engagement/channel-secret.ts`.

export type FounderChannelSendResult = { ok: true } | { ok: false; reason: string };

export interface FounderChannelAdapter {
  sendVerificationProbe(chatId: string, token: string, label?: string): Promise<FounderChannelSendResult>;
  sendMessage(chatId: string, token: string, content: string): Promise<FounderChannelSendResult>;
}

const TELEGRAM_API_BASE = "https://api.telegram.org";
// Task 3 (B2): request tới Telegram không được treo vô hạn — quá hạn thì trả {ok:false}
// để caller map sang lỗi thử lại được (ADR-FOUNDER-CHANNEL-001, Consequences).
const DEFAULT_TELEGRAM_TIMEOUT_MS = 10_000;

export interface TelegramBotApiAdapterOptions {
  timeoutMs?: number;
}

export class TelegramBotApiAdapter implements FounderChannelAdapter {
  private readonly timeoutMs: number;

  constructor(options: TelegramBotApiAdapterOptions = {}) {
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TELEGRAM_TIMEOUT_MS;
  }

  async sendVerificationProbe(chatId: string, token: string, label?: string): Promise<FounderChannelSendResult> {
    const text = label
      ? `Kênh nhận thông báo "${label}" đã được kết nối. Đây là tin nhắn xác minh.`
      : "Kênh nhận thông báo đã được kết nối. Đây là tin nhắn xác minh.";
    return this.sendMessage(chatId, token, text);
  }

  async sendMessage(chatId: string, token: string, content: string): Promise<FounderChannelSendResult> {
    try {
      const res = await fetch(`${TELEGRAM_API_BASE}/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text: content }),
        signal: AbortSignal.timeout(this.timeoutMs),
      });

      const body = await res.json().catch(() => null);
      if (!res.ok || !body || body.ok !== true) {
        const reason = (body && (body.description as string)) || `telegram_http_${res.status}`;
        return { ok: false, reason };
      }
      return { ok: true };
    } catch (err) {
      const reason = err instanceof Error ? err.message : "telegram_network_error";
      return { ok: false, reason };
    }
  }
}

let customFounderChannelAdapter: FounderChannelAdapter | null = null;

/**
 * Tiêm adapter test double (hoặc cấu hình khác) thay cho TelegramBotApiAdapter
 * thật. `null` khôi phục về mặc định. Dùng trong test — reset lại ở `afterEach`.
 */
export function setCustomFounderChannelAdapter(adapter: FounderChannelAdapter | null): void {
  customFounderChannelAdapter = adapter;
}

export function getFounderChannelAdapter(): FounderChannelAdapter {
  return customFounderChannelAdapter ?? new TelegramBotApiAdapter();
}
