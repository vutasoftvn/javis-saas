import { z } from "zod";

// Giới hạn độ dài từng trường để chặn payload quá khổ và input rác trước khi
// đưa vào email template — đây là lớp validate chặt, thay cho các kiểm tra
// truthy lỏng lẻo trước đây (chỉ check "có giá trị" chứ không giới hạn độ dài).
const earlyAccessSchema = z.object({
  fullName: z.string().trim().min(2).max(120),
  email: z.string().trim().toLowerCase().email().max(254),
  phone: z.string().trim().min(8).max(32),
  company: z.string().trim().min(2).max(160),
  role: z.string().trim().max(80).optional(),
  teamSize: z.string().trim().max(80).optional(),
  priorityInterest: z.string().trim().max(80).optional(),
  note: z.string().trim().max(2000).optional(),
});

export type EarlyAccessRegistrationInput = z.infer<typeof earlyAccessSchema>;

/**
 * Parse + validate dữ liệu đăng ký early access thô (chưa tin cậy) từ request
 * body. Ném lỗi ZodError khi input sai định dạng hoặc vượt giới hạn độ dài —
 * caller (route handler) chịu trách nhiệm bắt lỗi và trả HTTP 400.
 */
export function parseEarlyAccessRegistration(input: unknown): EarlyAccessRegistrationInput {
  return earlyAccessSchema.parse(input);
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
