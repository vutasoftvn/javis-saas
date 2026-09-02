#!/usr/bin/env node
// Task 11 — in trạng thái expiry của allowlist frontend API contract cho job
// CI `frontend-integration` (release-gate). Đây CHỈ là báo cáo hiển thị
// (không phải gate) — gate thật là `check_frontend_api_contracts.mjs` (chạy
// trong `make frontend-api-contract-check`, job `boundaries`), file này
// không lặp lại/thay thế logic gate đó.
import fs from "node:fs";

const path = "scripts/frontend-api-contract-allowlist.json";
const data = JSON.parse(fs.readFileSync(path, "utf8"));
const today = new Date().toISOString().slice(0, 10);
const entries = data.entries || [];

let needsAttention = 0;
for (const e of entries) {
  let status;
  if (!e.expires_on) {
    status = "NO EXPIRY (fails contract check)";
    needsAttention += 1;
  } else if (e.expires_on <= today) {
    status = "EXPIRED";
    needsAttention += 1;
  } else {
    status = `ok until ${e.expires_on}`;
  }
  console.log(`- ${e.method} ${e.path} — ${status}`);
}
console.log(`total entries: ${entries.length}, needs attention: ${needsAttention}`);
