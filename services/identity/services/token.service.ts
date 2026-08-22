import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod";

export interface JwtPayload {
  sub: string;
}

export function signAccessToken(userId: string): string {
  return jwt.sign({ sub: userId }, JWT_SECRET, { expiresIn: "7d" });
}

export function verifyAccessToken(token: string): JwtPayload {
  return jwt.verify(token, JWT_SECRET) as JwtPayload;
}
