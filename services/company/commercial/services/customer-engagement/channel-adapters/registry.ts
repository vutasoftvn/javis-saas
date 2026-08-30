import { ChannelAdapter } from "./contract";
import { ApiChannelAdapter } from "./api-channel.adapter";
import { ZaloChannelAdapter } from "./zalo-channel.adapter";
import { APIError } from "encore.dev/api";

function createDefaultRegistry(): Record<string, ChannelAdapter> {
  return {
    api: new ApiChannelAdapter(),
    zalo: new ZaloChannelAdapter(),
  };
}

let registry: Record<string, ChannelAdapter> = createDefaultRegistry();

export function registerChannelAdapter(channelType: string, adapter: ChannelAdapter): void {
  registry[channelType.toLowerCase()] = adapter;
}

// Chỉ dùng trong test: khôi phục registry adapter về trạng thái mặc định (api + zalo thật)
// để một test case ghi đè adapter (vd. fetchRunner giả) không rò rỉ sang test case/file khác
// chạy sau — đây là nguồn gây flakiness của bộ test outbound relay đã phát hiện trong audit.
export function resetChannelAdapterRegistryForTest(): void {
  registry = createDefaultRegistry();
}

export function getChannelAdapter(channelType: string): ChannelAdapter {
  const adapter = registry[channelType.toLowerCase()];
  if (!adapter) {
    throw APIError.invalidArgument(`unsupported channel type: ${channelType}`);
  }
  return adapter;
}
