import { ChannelAdapter } from "./contract";
import { ApiChannelAdapter } from "./api-channel.adapter";
import { ZaloChannelAdapter } from "./zalo-channel.adapter";
import { APIError } from "encore.dev/api";

const registry: Record<string, ChannelAdapter> = {
  api: new ApiChannelAdapter(),
  zalo: new ZaloChannelAdapter(),
};

export function registerChannelAdapter(channelType: string, adapter: ChannelAdapter): void {
  registry[channelType.toLowerCase()] = adapter;
}

export function getChannelAdapter(channelType: string): ChannelAdapter {
  const adapter = registry[channelType.toLowerCase()];
  if (!adapter) {
    throw APIError.invalidArgument(`unsupported channel type: ${channelType}`);
  }
  return adapter;
}
