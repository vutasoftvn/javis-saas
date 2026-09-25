import { describe, expect, it } from "vitest";
import { getPlatformUserProfile, updateCosaPreferences } from "../services/auth.service";
import { registerPlatformUser } from "./support/test-identity";

// Spec 2026-09-25 §8 — COSA chỉ ghi preference; dữ liệu liên hệ thuộc Core.

async function createUser() {
  return registerPlatformUser({
    email: `prefs-${Date.now()}-${Math.random()}@test.invalid`,
    password: "SecurePassword123",
    workspace_name: "Preference test workspace",
  });
}

describe("PATCH /platform/preferences/me", () => {
  it("persists locale, headline and bio in COSA", async () => {
    const session = await createUser();
    const updated = await updateCosaPreferences(session.user!.id, {
      preferredLocale: "en-US",
      headline: "Founder",
      bio: "Building COSA",
    });
    expect(updated.preferred_locale).toBe("en-US");
    expect(updated.headline).toBe("Founder");
    expect(updated.bio).toBe("Building COSA");
  });

  it("rejects Core-owned contact fields without writing them", async () => {
    const session = await createUser();
    const before = await getPlatformUserProfile(session.user!.id);

    for (const params of [
      { phone: "+84912345678" },
      { email: "x@test.invalid" },
      { display_name: "Someone Else" },
      { full_name: "Someone Else" },
      { avatar_url: "https://example.invalid/a.png" },
    ]) {
      await expect(updateCosaPreferences(session.user!.id, params)).rejects.toMatchObject({
        code: "invalid_argument",
      });
    }

    const after = await getPlatformUserProfile(session.user!.id);
    expect(after.phone).toBe(before.phone);
    expect(after.full_name).toBe(before.full_name);
    expect(after.avatar_url).toBe(before.avatar_url);
  });
});
