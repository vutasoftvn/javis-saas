import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.PLATFORM_JWT_SECRET || "cosa-super-secret-platform-jwt-key-change-in-prod";

export interface PlatformJwtPayload {
  sub: string;
  aud: "cosa" | "control_plane";
}

export function signPlatformToken(userId: string): string {
  return jwt.sign(
    {
      sub: userId,
      aud: "cosa",
    },
    JWT_SECRET,
    {
      expiresIn: "7d",
    }
  );
}

export function verifyPlatformToken(token: string): PlatformJwtPayload {
  return jwt.verify(token, JWT_SECRET) as PlatformJwtPayload;
}
