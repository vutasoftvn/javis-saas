import { APIError } from "encore.dev/api";

let customChannelSecretResolver: ((secretRef: string) => Promise<string | null>) | null = null;

export function setCustomChannelSecretResolver(
  resolver: ((secretRef: string) => Promise<string | null>) | null
) {
  customChannelSecretResolver = resolver;
}

export async function resolveChannelSecret(secretRef: string): Promise<string> {
  if (customChannelSecretResolver) {
    const res = await customChannelSecretResolver(secretRef);
    if (res) return res;
  }

  // Look up from env: CHANNEL_SECRET_<REF>
  const envVal = process.env[`CHANNEL_SECRET_${secretRef.toUpperCase()}`];
  if (envVal) {
    return envVal;
  }

  // For testing / dev default token conventions
  if (secretRef === "test_secret_ref" || secretRef === "sec_zalo_oa_vault_ref_1") {
    return "test_resolved_channel_secret_token";
  }

  throw APIError.failedPrecondition(`secret not resolvable: ${secretRef}`);
}
