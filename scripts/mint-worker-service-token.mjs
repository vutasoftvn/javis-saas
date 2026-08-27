#!/usr/bin/env node

/**
 * Mint a short-lived worker service JWT token.
 *
 * Invocation:
 *   WORKER_SERVICE_JWT_SECRET="..." node scripts/mint-worker-service-token.mjs <worker-id>
 *   Or: ./scripts/mint-worker-service-token.mjs <worker-id>
 *
 * Emits only the compact JWT to stdout.
 *
 * Note: Looks for jsonwebtoken in services/cosa/node_modules or services/company/node_modules
 */

import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = dirname(__dirname);

// Create a require function for the repo root to resolve node_modules
const require = createRequire(join(repoRoot, "package.json"));

// Try to find jsonwebtoken using require from different contexts
let jwt;
const tryContexts = [
  join(repoRoot, "services", "cosa", "package.json"),
  join(repoRoot, "services", "company", "package.json"),
  join(repoRoot, "package.json"),
];

for (const contextPath of tryContexts) {
  try {
    const contextRequire = createRequire(contextPath);
    jwt = contextRequire("jsonwebtoken");
    if (jwt && jwt.sign) break;
  } catch (e) {
    // Continue to next context
  }
}

if (!jwt || !jwt.sign) {
  console.error("Error: Could not find jsonwebtoken module. Install dependencies in services/cosa or services/company.");
  process.exit(1);
}

// Get worker ID from command line
const workerId = process.argv[2];
if (!workerId) {
  console.error("Usage: WORKER_SERVICE_JWT_SECRET=... ./scripts/mint-worker-service-token.mjs <worker-id>");
  process.exit(1);
}

// Read secret from environment
const secret = process.env.WORKER_SERVICE_JWT_SECRET;
if (!secret) {
  console.error("Error: WORKER_SERVICE_JWT_SECRET environment variable is required");
  process.exit(1);
}

// Reject weak secrets outside development
const nodeEnv = process.env.NODE_ENV || "development";
if (nodeEnv !== "development" && secret.length < 32) {
  console.error("Error: WORKER_SERVICE_JWT_SECRET must be at least 32 characters outside development");
  process.exit(1);
}

// Sign token with required claims
const now = Math.floor(Date.now() / 1000);
const expiresIn = 3600; // 1 hour expiry

const payload = {
  aud: "control_plane",
  role: "worker_service",
  sub: workerId,
  iss: "cosa_control_plane",
  iat: now,
  exp: now + expiresIn,
};

const token = jwt.sign(payload, secret, {
  algorithm: "HS256",
  noTimestamp: false,
});

// Emit only the token to stdout (no newlines or extra text)
process.stdout.write(token);
