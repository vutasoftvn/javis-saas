import { describe, it, expect } from "vitest";
import { healthz } from "../handlers/health.handler";

describe("Company Health Endpoint", () => {
  it("returns a response with status ok or error depending on database connectivity", async () => {
    const response = await healthz();

    expect(response).toBeDefined();
    expect(response.app).toBe("company");
    // Status phải là "ok" hoặc "error" tùy thuộc vào kết nối DB
    expect(["ok", "error"]).toContain(response.status);
    expect(response.version).toBeDefined();

    // Xác nhận response không chứa thông tin nhạy cảm như DSN, hostname, hay secret
    expect(JSON.stringify(response)).not.toMatch(/postgresql|password|secret|host/i);
  });

  it("includes app name, status, and version in response", async () => {
    const response = await healthz();

    expect(response).toHaveProperty("app");
    expect(response).toHaveProperty("status");
    expect(response).toHaveProperty("version");

    // Xác nhận chỉ có các thuộc tính này
    const keys = Object.keys(response).sort();
    expect(keys).toEqual(["app", "status", "version"]);
  });

  it("does not return database DSN or hostname", async () => {
    const response = await healthz();
    const responseJson = JSON.stringify(response);

    // Các thông tin này không được phép xuất hiện trong response
    expect(responseJson).not.toContain("127.0.0.1");
    expect(responseJson).not.toContain("localhost");
    expect(responseJson).not.toContain("5433");
    expect(responseJson).not.toContain("cosa");
  });
});
