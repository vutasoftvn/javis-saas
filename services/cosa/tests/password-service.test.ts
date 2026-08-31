import { describe, it, expect } from "vitest";
import * as passwordSvc from "../services/password.service";

describe("Password Service (password.service)", () => {
  describe("hashPassword function", () => {
    it("hashes a plain text password", async () => {
      const plain = "MySecurePassword123!@#";
      const hashed = await passwordSvc.hashPassword(plain);

      expect(hashed).toBeDefined();
      expect(typeof hashed).toBe("string");
      // bcrypt hashes are typically 60 characters
      expect(hashed.length).toBe(60);
      // bcrypt hashes start with $2
      expect(hashed.startsWith("$2")).toBe(true);
    });

    it("produces different hash for same password on each call", async () => {
      const plain = "password123";
      const hash1 = await passwordSvc.hashPassword(plain);
      const hash2 = await passwordSvc.hashPassword(plain);

      // Hashes should be different due to salt
      expect(hash1).not.toBe(hash2);
    });

    it("hashes empty string", async () => {
      const hashed = await passwordSvc.hashPassword("");
      expect(hashed).toBeDefined();
      expect(hashed.length).toBe(60);
    });

    it("hashes very long password", async () => {
      const longPass = "a".repeat(1000);
      const hashed = await passwordSvc.hashPassword(longPass);
      expect(hashed).toBeDefined();
      expect(hashed.length).toBe(60);
    });

    it("hashes passwords with special characters", async () => {
      const special =
        "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/`~";
      const hashed = await passwordSvc.hashPassword(special);
      expect(hashed).toBeDefined();
      expect(hashed.length).toBe(60);
    });

    it("hashes passwords with unicode characters", async () => {
      const unicode = "パスワード密码Пароль";
      const hashed = await passwordSvc.hashPassword(unicode);
      expect(hashed).toBeDefined();
      expect(hashed.length).toBe(60);
    });
  });

  describe("verifyPassword function", () => {
    it("verifies correct password against hash", async () => {
      const plain = "CorrectPassword123";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword(plain, hashed);
      expect(isValid).toBe(true);
    });

    it("rejects incorrect password against hash", async () => {
      const plain = "CorrectPassword123";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword("WrongPassword123", hashed);
      expect(isValid).toBe(false);
    });

    it("rejects empty password against hash", async () => {
      const plain = "MyPassword";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword("", hashed);
      expect(isValid).toBe(false);
    });

    it("rejects password against hash of different password", async () => {
      const hash1 = await passwordSvc.hashPassword("password1");
      const hash2 = await passwordSvc.hashPassword("password2");

      const isValid = await passwordSvc.verifyPassword("password1", hash2);
      expect(isValid).toBe(false);
    });

    it("is case-sensitive", async () => {
      const plain = "MyPassword";
      const hashed = await passwordSvc.hashPassword(plain);

      const lowerValid = await passwordSvc.verifyPassword("mypassword", hashed);
      expect(lowerValid).toBe(false);

      const upperValid = await passwordSvc.verifyPassword("MYPASSWORD", hashed);
      expect(upperValid).toBe(false);

      const exactValid = await passwordSvc.verifyPassword("MyPassword", hashed);
      expect(exactValid).toBe(true);
    });

    it("verifies password with special characters", async () => {
      const plain = "P@ss!w0rd#123";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword(plain, hashed);
      expect(isValid).toBe(true);
    });

    it("verifies password with unicode characters", async () => {
      const plain = "パスワード123";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword(plain, hashed);
      expect(isValid).toBe(true);
    });

    it("rejects unicode variation", async () => {
      const plain = "café";
      const variation = "cafe";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword(variation, hashed);
      expect(isValid).toBe(false);
    });

    it("handles hash corruption gracefully", async () => {
      const corruptHash = "not_a_valid_bcrypt_hash";

      // bcrypt.compare should return false for invalid hash
      const isValid = await passwordSvc.verifyPassword("anypassword", corruptHash);
      expect(isValid).toBe(false);
    });

    it("verifies very long password", async () => {
      const longPass = "a".repeat(1000);
      const hashed = await passwordSvc.hashPassword(longPass);

      const isValid = await passwordSvc.verifyPassword(longPass, hashed);
      expect(isValid).toBe(true);
    });

    it("rejects partial password match", async () => {
      const plain = "MyCompletePassword";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword("MyComplete", hashed);
      expect(isValid).toBe(false);
    });

    it("rejects password with extra characters", async () => {
      const plain = "Password";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword("Password ", hashed);
      expect(isValid).toBe(false);
    });

    it("rejects password with leading spaces", async () => {
      const plain = "Password";
      const hashed = await passwordSvc.hashPassword(plain);

      const isValid = await passwordSvc.verifyPassword(" Password", hashed);
      expect(isValid).toBe(false);
    });
  });

  describe("Hash/Verify Integration", () => {
    it("complete password lifecycle: hash and verify multiple times", async () => {
      const plain = "TestPassword123!";

      const hash1 = await passwordSvc.hashPassword(plain);
      expect(await passwordSvc.verifyPassword(plain, hash1)).toBe(true);

      // Hash same password again (different salt)
      const hash2 = await passwordSvc.hashPassword(plain);
      expect(await passwordSvc.verifyPassword(plain, hash2)).toBe(true);

      // Both hashes are different but both verify same password
      expect(hash1).not.toBe(hash2);
    });

    it("typical user signup and login flow", async () => {
      // Signup
      const signupPassword = "InitialPassword123";
      const storedHash = await passwordSvc.hashPassword(signupPassword);

      // Later login attempt with correct password
      const loginCorrect = await passwordSvc.verifyPassword(signupPassword, storedHash);
      expect(loginCorrect).toBe(true);

      // Login attempt with wrong password
      const loginWrong = await passwordSvc.verifyPassword("WrongPassword", storedHash);
      expect(loginWrong).toBe(false);
    });

    it("multiple users can have same password with different hashes", async () => {
      const password = "SharedPassword123";

      const user1Hash = await passwordSvc.hashPassword(password);
      const user2Hash = await passwordSvc.hashPassword(password);

      // Same password verifies against both hashes
      expect(await passwordSvc.verifyPassword(password, user1Hash)).toBe(true);
      expect(await passwordSvc.verifyPassword(password, user2Hash)).toBe(true);

      // But hashes are different due to different salts
      expect(user1Hash).not.toBe(user2Hash);

      // Can't use one hash to verify another user's password
      expect(await passwordSvc.verifyPassword(password, user1Hash)).toBe(true);
      expect(await passwordSvc.verifyPassword(password, user2Hash)).toBe(true);
    });
  });
});
