import jwt from "jsonwebtoken";
import { secret } from "encore.dev/config";

const jwtSecret = secret("ControlPlaneJwtSecret");

function getSecret(): string {
  return jwtSecret() || process.env.CONTROL_PLANE_JWT_SECRET || process.env.IDENTITY_JWT_SECRET || "dev-local-secret-do-not-use-in-prod";
}

export interface PlatformTokenPayload {
  sub: string;
  aud?: string;
}

export function signPlatformToken(userId: string, expiresInMinutes = 60 * 24 * 7): string {
  return jwt.sign(
    {
      sub: String(userId),
      aud: "control_plane",
    },
    getSecret(),
    {
      algorithm: "HS256",
      expiresIn: `${expiresInMinutes}m`,
    }
  );
}

export function verifyPlatformToken(token: string): PlatformTokenPayload {
  const decoded = jwt.verify(token, getSecret(), {
    algorithms: ["HS256"],
    audience: "control_plane",
  });
  if (typeof decoded === "string" || !decoded.sub) {
    throw new Error("invalid token payload");
  }
  return { sub: String(decoded.sub), aud: "control_plane" };
}
