import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const dir = join(__dirname, "../migrations");
const up = readFileSync(join(dir, "006_core_identity_projection.up.sql"), "utf8");
const down = readFileSync(join(dir, "006_core_identity_projection.down.sql"), "utf8");

describe("migration 006: user và workspace là bản chiếu của backend/core", () => {
  it("cho phép user không có mật khẩu cục bộ", () => {
    expect(up).toMatch(/ALTER TABLE cosa\.users\s+ALTER COLUMN hashed_password DROP NOT NULL/);
  });

  it("bỏ FK owner_user_id vì chủ sở hữu do core quyết định", () => {
    expect(up).toMatch(/DROP CONSTRAINT IF EXISTS platform_workspaces_owner_user_id_fkey/);
  });

  it("có file down đảo ngược", () => {
    expect(down).toMatch(/SET NOT NULL/);
    expect(down).toMatch(/platform_workspaces_owner_user_id_fkey/);
  });
});
