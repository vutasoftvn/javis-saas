// B5 (Task 6b, plan hub vận hành đợt 2) / ADR-FOUNDER-CHANNEL-001 mục 8 — preflight cho
// `founder.notify.send` dùng bởi lịch nền uỷ quyền trước: worker gọi endpoint này TRƯỚC khi
// tạo conversation/gọi model, để phát hiện kênh đã thu hồi hoặc founder mất quyền MÀ KHÔNG
// tiêu token hay bắt đầu chạy agent trước rồi mới biết không gửi được.
//
// Guard giống hệt `POST /identity/founder-notifications/send` (cùng capability, cùng cổng
// delegation): `requireWorkspaceAccess(..., { agentCapabilities: [AGENT_CAP.FOUNDER_NOTIFY_SEND] })`.
// Dùng lại đúng logic kiểm role/workforce member + `resolveUsableChannelForFounder` qua
// `preflightFounderNotificationChannel` (tách hàm dùng chung ở service, không nhân bản) —
// KHÔNG gửi gì, không đọc secret, không gọi adapter Telegram.
//
// GET (không phải POST): preflight không có side effect, chỉ query param `channelKind` tuỳ
// chọn — không có payload allowlist nào cần bảo vệ khỏi decoder bỏ-qua-field-lạ của Encore
// (khác `send`, endpoint này không có body), nên dùng typed `api()` bình thường, không cần
// `api.raw`.
import { api, APIError, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import {
  preflightFounderNotificationChannel,
  type FounderChannelPreflightResult,
} from "../services/founder-notification-send.service";
import type { FounderNotificationChannelKind } from "../services/founder-notification-channel.service";

const SUPPORTED_KINDS: ReadonlySet<string> = new Set<FounderNotificationChannelKind>(["telegram"]);

export interface FounderNotificationPreflightParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  channelKind?: Query<string>;
}

export const founderNotificationPreflightApi = api(
  { expose: true, method: "GET", path: "/identity/founder-notifications/preflight" },
  async (
    params: FounderNotificationPreflightParams
  ): Promise<FounderChannelPreflightResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.FOUNDER_NOTIFY_SEND],
    });

    let channelKind: FounderNotificationChannelKind | undefined;
    if (params.channelKind !== undefined && params.channelKind !== "") {
      if (!SUPPORTED_KINDS.has(params.channelKind)) {
        throw APIError.invalidArgument(
          "founder_notify_invalid_payload: channelKind không được hỗ trợ"
        );
      }
      channelKind = params.channelKind as FounderNotificationChannelKind;
    }

    return preflightFounderNotificationChannel(ctx, channelKind);
  }
);
