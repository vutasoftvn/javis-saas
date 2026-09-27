// Task 2 (B1) / ADR-FOUNDER-CHANNEL-001 — endpoint founder-only cho kênh nhận
// thông báo ngoài của founder. Cùng pattern
// `services/company/operations/handlers/founder-asset-query.handler.ts`
// (requireWorkspaceAccess + requireFounderCommand, Header<"Authorization">,
// Header<"X-Workspace-Id">, trả MvpSuccess<T>). `expose: true` — đây là API
// founder gọi từ frontend, không phải nội bộ service-to-service (khác với
// endpoint `founder.notify.send` của B2, sẽ là expose: false).
import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createFounderNotificationChannel,
  verifyFounderNotificationChannel,
  revokeFounderNotificationChannel,
  listFounderNotificationChannels,
  type FounderNotificationChannelDto,
  type FounderNotificationChannelKind,
} from "../services/founder-notification-channel.service";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";

// Fix review #1 — `secretRef` KHÔNG còn là tham số của request: client
// không được chọn giá trị này (server tự sinh trong service từ id snowflake
// vừa tạo), nên không có field nào cho phép founder trỏ tới secret của kênh
// khác.
export interface CreateFounderNotificationChannelParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  kind: FounderNotificationChannelKind;
  chatId: string;
  label?: string;
}

export const createFounderNotificationChannelApi = api(
  { expose: true, method: "POST", path: "/identity/founder-notification-channels" },
  async (
    params: CreateFounderNotificationChannelParams
  ): Promise<MvpSuccess<FounderNotificationChannelDto>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createFounderNotificationChannel(tenantCtx, {
      kind: params.kind,
      chatId: params.chatId,
      label: params.label,
    });
  }
);

export interface VerifyFounderNotificationChannelParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export const verifyFounderNotificationChannelApi = api(
  { expose: true, method: "POST", path: "/identity/founder-notification-channels/:id/verify" },
  async (
    params: VerifyFounderNotificationChannelParams
  ): Promise<MvpSuccess<FounderNotificationChannelDto>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return verifyFounderNotificationChannel(tenantCtx, params.id);
  }
);

export interface RevokeFounderNotificationChannelParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export const revokeFounderNotificationChannelApi = api(
  { expose: true, method: "POST", path: "/identity/founder-notification-channels/:id/revoke" },
  async (
    params: RevokeFounderNotificationChannelParams
  ): Promise<MvpSuccess<FounderNotificationChannelDto>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return revokeFounderNotificationChannel(tenantCtx, params.id);
  }
);

export interface ListFounderNotificationChannelsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const listFounderNotificationChannelsApi = api(
  { expose: true, method: "GET", path: "/identity/founder-notification-channels" },
  async (
    params: ListFounderNotificationChannelsParams
  ): Promise<MvpSuccess<readonly FounderNotificationChannelDto[]>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listFounderNotificationChannels(tenantCtx);
  }
);
