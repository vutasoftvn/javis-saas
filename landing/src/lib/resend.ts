import { Resend } from "resend";
import { escapeHtml } from "./early-access";

// Dữ liệu đầu vào để dựng nội dung email — KHÁC với EarlyAccessRegistration
// bền vững ở early-access-store.ts (type đó có thêm id/status/ISO timestamp
// phục vụ lưu trữ, còn type này chỉ phục vụ render template email với
// registeredAt đã format hiển thị sẵn).
export interface EarlyAccessEmailData {
  fullName: string;
  email: string;
  phone: string;
  company: string;
  role?: string;
  teamSize?: string;
  priorityInterest: string;
  note?: string;
  accessCode: string;
  registeredAt: string;
}

const resendApiKey = process.env.RESEND_API_KEY;
const resendFromEmail = process.env.RESEND_FROM_EMAIL || "COSA OS <onboarding@resend.dev>";
const adminNotificationEmail = process.env.ADMIN_NOTIFICATION_EMAIL;

const resendClient = resendApiKey ? new Resend(resendApiKey) : null;

/**
 * True khi chưa cấu hình RESEND_API_KEY thật (môi trường dev/thử nghiệm) —
 * route handler dùng giá trị này để quyết định trạng thái lưu trữ ban đầu
 * ("simulated") TRƯỚC khi gọi sendEarlyAccessEmails(), vì việc lưu bền vững
 * phải xảy ra trước bước gửi/queue email theo đúng thứ tự bắt buộc.
 */
export function isEarlyAccessEmailSimulated(): boolean {
  return !resendClient || !resendApiKey || resendApiKey.startsWith("re_your_api_key");
}

/**
 * Gửi email xác nhận quyền truy cập sớm cho Người dùng và Thông báo Lead mới cho Ban Quản trị
 */
export async function sendEarlyAccessEmails(data: EarlyAccessEmailData): Promise<{
  userEmailSent: boolean;
  adminEmailSent: boolean;
  simulated?: boolean;
  error?: string;
  providerMessageId?: string;
}> {
  // Nếu chưa cấu hình API Key, ghi nhận log và phản hồi mô phỏng (KHÔNG email
  // nào thực sự được gửi) — route handler dựa vào cờ `simulated` để biết đây
  // là môi trường dev/chưa cấu hình, không phải một lần gửi thật thất bại.
  // KHÔNG log fullName/email/accessCode thô — chỉ log company (không phải PII
  // định danh cá nhân) để tránh rò rỉ dữ liệu nhạy cảm vào log hệ thống.
  if (isEarlyAccessEmailSimulated()) {
    console.log(
      `[Resend Simulation] No RESEND_API_KEY configured. Early access registration logged for company:`,
      data.company
    );
    return {
      userEmailSent: false,
      adminEmailSent: false,
      simulated: true,
    };
  }

  let userEmailSent = false;
  let adminEmailSent = false;
  let providerMessageId: string | undefined;

  try {
    // 1. Gửi email xác nhận Early Access tới Người dùng
    const userHtml = generateUserConfirmationEmail(data);
    const userRes = await resendClient!.emails.send({
      from: resendFromEmail,
      to: [data.email],
      subject: `[COSA OS] Xác nhận Quyền Sử Dụng Sớm - Mã VIP: ${data.accessCode}`,
      html: userHtml,
    });

    if (userRes.error) {
      // Chỉ log `.name` (mã lỗi cố định dạng enum của Resend, vd.
      // "validation_error"), KHÔNG log `.message` — message tự do có thể
      // echo lại giá trị người dùng nhập (vd. địa chỉ email không hợp lệ)
      // tuỳ theo cách Resend diễn giải lỗi.
      console.error("[Resend User Email Error]:", userRes.error.name);
    } else {
      userEmailSent = true;
      providerMessageId = userRes.data?.id;
    }

    // 2. Gửi email thông báo cho Ban Quản Trị (nếu có ADMIN_NOTIFICATION_EMAIL)
    if (adminNotificationEmail) {
      const adminHtml = generateAdminNotificationEmail(data);
      const adminRes = await resendClient!.emails.send({
        from: resendFromEmail,
        to: [adminNotificationEmail],
        subject: `🔥 [Lead Mới] ${data.fullName} (${data.company}) vừa đăng ký Early Access`,
        html: adminHtml,
      });

      if (adminRes.error) {
        console.error("[Resend Admin Email Error]:", adminRes.error.name);
      } else {
        adminEmailSent = true;
      }
    }

    return {
      userEmailSent,
      adminEmailSent,
      providerMessageId,
    };
  } catch (error: unknown) {
    // Log tên loại lỗi (class name cố định, vd. "TypeError"), KHÔNG log
    // `.message` — exception ở tầng SDK/mạng hiếm khi chứa PII nhưng không
    // có gì đảm bảo tuyệt đối, nên vẫn tránh forward nguyên văn để nhất
    // quán với chính sách log của toàn bộ file này.
    console.error("[Resend Delivery Exception]:", error instanceof Error ? error.name : "UnknownError");
    const errorMessage = "Unknown email delivery error";
    return {
      userEmailSent,
      adminEmailSent,
      error: errorMessage,
    };
  }
}

function generateUserConfirmationEmail(data: EarlyAccessEmailData): string {
  // Escape mọi giá trị người dùng nhập trước khi nội suy vào HTML — chặn
  // stored/reflected XSS trong email client của người nhận (chính user đăng
  // ký, vì email này gửi tới địa chỉ họ vừa nhập).
  const fullName = escapeHtml(data.fullName);
  const company = escapeHtml(data.company);
  const email = escapeHtml(data.email);
  const phone = escapeHtml(data.phone);
  const priorityInterest = escapeHtml(data.priorityInterest);
  const accessCode = escapeHtml(data.accessCode);
  const registeredAt = escapeHtml(data.registeredAt);
  return `
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>COSA OS - Xác nhận Quyền Sử Dụng Sớm</title>
</head>
<body style="margin: 0; padding: 0; background-color: #070c18; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #070c18; padding: 40px 10px;">
    <tr>
      <td align="center">
        <table width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #0d172a; border-radius: 16px; border: 1px solid #1e293b; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
          
          <!-- Header -->
          <tr>
            <td style="padding: 36px 40px 24px; background: linear-gradient(135deg, #0d172a 0%, #0a1122 100%); border-bottom: 1px solid #1e293b; text-align: left;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <span style="display: inline-block; font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: 1px;">
                      COSA<span style="color: #00f0ff;">.OS</span>
                    </span>
                    <p style="margin: 4px 0 0; font-size: 12px; color: #94a3b8; letter-spacing: 0.5px; text-transform: uppercase;">
                      The AI Operating System for Startups
                    </p>
                  </td>
                  <td align="right">
                    <span style="display: inline-block; padding: 6px 14px; background-color: rgba(0, 240, 255, 0.1); border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 20px; color: #00f0ff; font-size: 11px; font-weight: 700; font-family: monospace;">
                      EARLY ACCESS BATCH #1
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 36px 40px;">
              <h1 style="margin: 0 0 16px; font-size: 22px; font-weight: 700; color: #ffffff; line-height: 1.4;">
                Chúc mừng <span style="color: #00f0ff;">${fullName}</span>,<br>
                Bạn đã được ghi nhận trong danh sách Early Access!
              </h1>
              
              <p style="margin: 0 0 24px; font-size: 15px; color: #cbd5e1; line-height: 1.6;">
                Cảm ơn bạn và đội ngũ <strong>${company}</strong> đã quan tâm đến hệ điều hành doanh nghiệp AI <strong>COSA OS</strong>. Chúng tôi rất hào hứng được đồng hành cùng bạn trên hành trình tự trị hóa vận hành.
              </p>

              <!-- VIP Pass Box -->
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #070c18; border: 1px solid #00f0ff; border-radius: 12px; margin-bottom: 28px;">
                <tr>
                  <td style="padding: 20px 24px;">
                    <p style="margin: 0 0 6px; font-size: 11px; font-family: monospace; color: #94a3b8; text-transform: uppercase;">
                      MÃ THẺ TRUY CẬP SỚM (VIP ACCESS CODE)
                    </p>
                    <p style="margin: 0; font-size: 26px; font-weight: 800; color: #00f0ff; letter-spacing: 2px; font-family: monospace;">
                      ${accessCode}
                    </p>
                    <p style="margin: 8px 0 0; font-size: 12px; color: #64748b;">
                      Đăng ký lúc: ${registeredAt}
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Registration Summary -->
              <h3 style="margin: 0 0 14px; font-size: 14px; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">
                Thông Tin Xác Nhận:
              </h3>
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #070c18; border-radius: 8px; margin-bottom: 28px; font-size: 13px;">
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; width: 40%;">Doanh nghiệp / Dự án:</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #ffffff; font-weight: 600;">${company}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8;">Email:</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #ffffff;">${email}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8;">Số điện thoại / Zalo:</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #ffffff;">${phone}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; color: #94a3b8;">Nhu cầu trọng tâm:</td>
                  <td style="padding: 12px 16px; color: #38bdf8; font-weight: 600;">${priorityInterest}</td>
                </tr>
              </table>

              <!-- What to expect -->
              <h3 style="margin: 0 0 12px; font-size: 14px; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">
                Bước Tiếp Theo Là Gì?
              </h3>
              <ol style="margin: 0 0 28px; padding-left: 20px; font-size: 14px; color: #cbd5e1; line-height: 1.7;">
                <li><strong>Khảo sát nhu cầu riêng biệt:</strong> Đội ngũ giải pháp COSA OS sẽ liên hệ qua Zalo/Email trong vòng 2-4 giờ làm việc.</li>
                <li><strong>Cung cấp tài khoản trải nghiệm:</strong> Kích hoạt Workspace thử nghiệm 14 ngày trọn gói kèm kịch bản mẫu cho ngành nghề của bạn.</li>
                <li><strong>Buổi Demo 1-on-1:</strong> Hướng dẫn kết nối cơ sở dữ liệu, thiết lập OKRs 12 tuần và điều hành bằng Giọng nói Realtime.</li>
              </ol>

              <div style="text-align: center; padding-top: 10px;">
                <a href="https://zalo.me" style="display: inline-block; padding: 14px 28px; background: linear-gradient(90deg, #00f0ff, #0072ff); color: #070c18; font-weight: 700; font-size: 14px; text-decoration: none; border-radius: 10px; box-shadow: 0 4px 20px rgba(0, 240, 255, 0.4);">
                  Liên Hệ Trực Tiếp Với Đội Ngũ Sáng Lập
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px; background-color: #070c18; border-top: 1px solid #1e293b; text-align: center; font-size: 12px; color: #64748b;">
              <p style="margin: 0 0 6px;">COSA OS · Create. Operate. Scale. Automate.</p>
              <p style="margin: 0;">Kiến trúc Hybrid PostgreSQL Local + Supabase Central · On-Premise Data Sovereignty</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `;
}

function generateAdminNotificationEmail(data: EarlyAccessEmailData): string {
  // Escape mọi giá trị người dùng nhập trước khi nội suy vào HTML gửi cho
  // Ban Quản Trị — đây chính là điểm stored/reflected XSS bị khai thác nếu
  // không escape, vì nội dung này được người đọc email mở trực tiếp.
  const fullName = escapeHtml(data.fullName);
  const company = escapeHtml(data.company);
  const email = escapeHtml(data.email);
  const phone = escapeHtml(data.phone);
  const role = escapeHtml(data.role || "Chưa cung cấp");
  const teamSize = escapeHtml(data.teamSize || "Chưa cung cấp");
  const priorityInterest = escapeHtml(data.priorityInterest);
  const note = escapeHtml(data.note || "Không có");
  const accessCode = escapeHtml(data.accessCode);
  const registeredAt = escapeHtml(data.registeredAt);
  // encodeURIComponent cho giá trị attribute của mailto:/tel: (chặn phá vỡ
  // attribute qua ký tự đặc biệt trong URL scheme), giữ nguyên text hiển thị
  // đã escape ở trên.
  const mailtoHref = encodeURIComponent(data.email);
  const telHref = encodeURIComponent(data.phone);
  return `
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f8fafc; padding: 20px; color: #0f172a;">
  <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 1px solid #e2e8f0;">
    <h2 style="color: #0f172a; border-bottom: 2px solid #00f0ff; padding-bottom: 10px;">
      🚀 Có Đăng Ký Early Access Mới!
    </h2>
    <p><strong>Mã vé:</strong> ${accessCode}</p>
    <p><strong>Thời gian:</strong> ${registeredAt}</p>
    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee; width: 35%;"><strong>Họ và tên:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${fullName}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Email:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;"><a href="mailto:${mailtoHref}">${email}</a></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Số điện thoại:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;"><a href="tel:${telHref}">${phone}</a></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Công ty:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${company}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Chức vụ:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${role}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Quy mô đội ngũ:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${teamSize}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Nhu cầu trọng tâm:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee; color: #0284c7;"><strong>${priorityInterest}</strong></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Ghi chú / Câu hỏi:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${note}</td></tr>
    </table>
    <p style="margin-top: 20px; font-size: 12px; color: #64748b;">Hệ thống thông báo tự động từ COSA OS Landing via Resend API.</p>
  </div>
</body>
</html>
  `;
}
