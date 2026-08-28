import crypto from "node:crypto";
import { APIError } from "encore.dev/api";

export type VerificationConfig = {
  scheme: "hmac_sha256" | "none";
  secretRef: string;
  header: string;
  encoding: "hex" | "base64";
  signedPayload: "raw" | "raw_plus_timestamp";
  timestampHeader?: string;
  skewSeconds: number;
};

// Global in-memory map or test resolver for verification configs
let customVerificationConfigResolver: ((ref: string) => Promise<VerificationConfig | null>) | null = null;

export function setVerificationConfigResolverForTest(
  resolver: ((ref: string) => Promise<VerificationConfig | null>) | null
) {
  customVerificationConfigResolver = resolver;
}

export async function resolveVerificationConfig(ref: string): Promise<VerificationConfig> {
  if (customVerificationConfigResolver) {
    const config = await customVerificationConfigResolver(ref);
    if (config) return config;
  }

  // Look up from env: VERIFICATION_CONFIG_<REF>
  const envVal = process.env[`VERIFICATION_CONFIG_${ref.toUpperCase()}`];
  if (envVal) {
    try {
      return JSON.parse(envVal) as VerificationConfig;
    } catch {
      // Fallback if env is a raw secret
    }
  }

  // Default fallback for known test / local ref conventions
  if (ref && (ref.startsWith("sec_") || ref.startsWith("cfg_"))) {
    return {
      scheme: "hmac_sha256",
      secretRef: ref,
      header: "X-Zalo-Signature",
      encoding: "hex",
      signedPayload: "raw",
      skewSeconds: 300,
    };
  }

  throw APIError.failedPrecondition(`verification config not resolvable: ${ref}`);
}

export function verifyHmac(
  rawBody: Buffer,
  headers: Record<string, string | undefined>,
  config: VerificationConfig,
  secretKey: string
): void {
  if (config.scheme === "none") return;

  const headerKey = config.header.toLowerCase();
  let receivedSig = "";
  for (const [k, v] of Object.entries(headers)) {
    if (k.toLowerCase() === headerKey && v) {
      receivedSig = v;
      break;
    }
  }

  if (!receivedSig) {
    throw APIError.unauthenticated(`missing channel signature header: ${config.header}`);
  }

  // Clean prefix if signature is in format "mac=..." or "sha256=..."
  if (receivedSig.startsWith("mac=")) {
    receivedSig = receivedSig.slice(4);
  } else if (receivedSig.startsWith("sha256=")) {
    receivedSig = receivedSig.slice(7);
  }

  // Verify timestamp skew if configured
  if (config.timestampHeader) {
    const tsHeaderKey = config.timestampHeader.toLowerCase();
    let tsVal = "";
    for (const [k, v] of Object.entries(headers)) {
      if (k.toLowerCase() === tsHeaderKey && v) {
        tsVal = v;
        break;
      }
    }
    if (tsVal) {
      const parsedTs = Number(tsVal);
      if (!isNaN(parsedTs)) {
        const nowMs = Date.now();
        const tsMs = parsedTs > 1e12 ? parsedTs : parsedTs * 1000;
        const diffSec = Math.abs(nowMs - tsMs) / 1000;
        if (diffSec > config.skewSeconds) {
          throw APIError.unauthenticated(`signature timestamp expired / skew exceeded (${diffSec}s > ${config.skewSeconds}s)`);
        }
      }
    }
  }

  let payloadToSign = rawBody;
  if (config.signedPayload === "raw_plus_timestamp" && config.timestampHeader) {
    const tsVal = headers[config.timestampHeader.toLowerCase()] || "";
    payloadToSign = Buffer.concat([Buffer.from(tsVal, "utf-8"), rawBody]);
  }

  const computedSig = crypto.createHmac("sha256", secretKey).update(payloadToSign).digest(config.encoding);

  const receivedBuffer = Buffer.from(receivedSig, config.encoding);
  const computedBuffer = Buffer.from(computedSig, config.encoding);

  if (
    receivedBuffer.length !== computedBuffer.length ||
    !crypto.timingSafeEqual(receivedBuffer, computedBuffer)
  ) {
    throw APIError.unauthenticated("invalid channel signature");
  }
}
