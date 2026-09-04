import { z } from "zod";

// Giới hạn độ dài từng trường để chặn payload quá khổ và input rác trước khi
// đưa vào email template — đây là lớp validate chặt, thay cho các kiểm tra
// truthy lỏng lẻo trước đây (chỉ check "có giá trị" chứ không giới hạn độ dài).
const earlyAccessSchema = z.object({
  fullName: z
    .string()
    .trim()
    .max(120)
    .optional()
    .transform((val) => (val && val.length > 0 ? val : "Khách hàng Tiềm năng")),
  email: z.string().trim().toLowerCase().email().max(254),
  phone: z
    .string()
    .trim()
    .max(32)
    .optional()
    .transform((val) => (val && val.length > 0 ? val : "Liên hệ qua Email")),
  company: z
    .string()
    .trim()
    .max(160)
    .optional()
    .transform((val) => (val && val.length > 0 ? val : "Cá nhân / Doanh nghiệp")),
  userSegment: z
    .string()
    .trim()
    .max(80)
    .optional()
    .transform((val) => (val && val.length > 0 ? val : "OPC (Doanh nghiệp 1 người)")),
  projectName: z
    .string()
    .trim()
    .max(160)
    .optional(),
  role: z.string().trim().max(80).optional(),
  teamSize: z.string().trim().max(80).optional(),
  priorityInterest: z
    .string()
    .trim()
    .max(80)
    .optional()
    .transform((val) => (val && val.length > 0 ? val : "Gói Free - 1 Workspace & 1 Project")),
  note: z.string().trim().max(2000).optional(),
  turnstileToken: z.string().trim().max(4096).optional(),
  website: z.string().trim().max(200).optional(),
});

export type EarlyAccessRegistrationInput = z.infer<typeof earlyAccessSchema>;

export const personaDiscoverySchema = z.object({
  email: z.string().trim().toLowerCase().email().max(254),
  firstProjectGoal: z.string().trim().max(250).optional(),
  biggestChallenge: z.array(z.string().trim().max(250)).max(5).optional(),
  aiAutonomyLevel: z.enum(["L0", "L1", "L2"]).optional().default("L1"),
  targetTimelineWeeks: z.number().int().positive().max(52).optional(),
  notes: z.string().trim().max(2000).optional(),
});

export type PersonaDiscoveryInput = z.infer<typeof personaDiscoverySchema>;

export function parsePersonaDiscovery(input: unknown): PersonaDiscoveryInput {
  return personaDiscoverySchema.parse(input);
}

/**
 * Parse + validate dữ liệu đăng ký early access thô (chưa tin cậy) từ request
 * body. Ném lỗi ZodError khi input sai định dạng hoặc vượt giới hạn độ dài —
 * caller (route handler) chịu trách nhiệm bắt lỗi và trả HTTP 400.
 */
export function parseEarlyAccessRegistration(input: unknown): EarlyAccessRegistrationInput {
  return earlyAccessSchema.parse(input);
}

/**
 * Xác định môi trường production theo cách chuẩn của Next.js/Node
 * (NODE_ENV) — dùng để bật bắt buộc xác minh Turnstile và để các adapter
 * durable (store/rate-limit) fail loud khi thiếu cấu hình, thay vì đoán
 * theo domain hay header có thể bị giả mạo.
 */
export function isProductionEnvironment(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Xác minh token Cloudflare Turnstile qua API siteverify chính thức. CHỈ
 * được gọi khi isProductionEnvironment() === true — ở production mà thiếu
 * TURNSTILE_SECRET_KEY thì throw (fail loud) thay vì âm thầm bỏ qua CAPTCHA,
 * vì bỏ qua sẽ vô hiệu hoá toàn bộ lớp chống bot mà không ai nhận ra.
 */
export async function verifyTurnstileToken(
  token: string | undefined,
  remoteIp: string
): Promise<boolean> {
  const secretKey = process.env.TURNSTILE_SECRET_KEY;
  if (!secretKey) {
    return true; // Không chặn người dùng nếu hệ thống chưa bật Turnstile CAPTCHA
  }
  if (!token) {
    return false;
  }
  try {
    const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ secret: secretKey, response: token, remoteip: remoteIp }),
    });
    const result = (await response.json()) as { success?: boolean };
    return result.success === true;
  } catch (error: unknown) {
    // Không log token/IP thô — chỉ log rằng bước xác minh gặp lỗi mạng/API.
    console.error(
      "[Turnstile Verification Error]:",
      error instanceof Error ? error.message : "unknown error"
    );
    return false;
  }
}

// Escape các ký tự HTML metacharacter trước khi nội suy giá trị người dùng
// nhập vào body email HTML — chặn stored/reflected XSS vào email client của
// người đọc thông báo (admin) và người dùng đăng ký.
export const escapeHtml = (value: string) =>
  value.replace(
    /[&<>"']/g,
    (char) =>
      (
        {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        } as Record<string, string>
      )[char]!
  );
