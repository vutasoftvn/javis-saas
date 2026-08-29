import { defineConfig } from "vitest/config";
import fs from "fs";
import { execSync } from "child_process";

if (!process.env.ENCORE_RUNTIME_LIB) {
  const commonPaths = [
    "/opt/homebrew/Cellar/encore/1.58.2/libexec/runtimes/js/encore-runtime.node",
    "/usr/local/Cellar/encore/1.58.2/libexec/runtimes/js/encore-runtime.node",
  ];
  for (const p of commonPaths) {
    if (fs.existsSync(p)) {
      process.env.ENCORE_RUNTIME_LIB = p;
      break;
    }
  }
  if (!process.env.ENCORE_RUNTIME_LIB) {
    try {
      const found = execSync(
        "find /opt/homebrew/Cellar/encore /usr/local/Cellar/encore -name 'encore-runtime.node' 2>/dev/null | head -n 1",
        { encoding: "utf-8" }
      ).trim();
      if (found) {
        process.env.ENCORE_RUNTIME_LIB = found;
      }
    } catch {
      // Ignore fallback failure
    }
  }
}

if (!process.env.WORKSPACE_DATABASE_URL) {
  process.env.WORKSPACE_DATABASE_URL = "postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable";
}


export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    fileParallelism: false,
  },
});
