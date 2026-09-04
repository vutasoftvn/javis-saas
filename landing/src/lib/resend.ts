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
  userSegment?: string;
  projectName?: string;
  role?: string;
  teamSize?: string;
  priorityInterest: string;
  note?: string;
  accessCode: string;
  registeredAt: string;
  surveyUrl?: string;
}

const resendApiKey = process.env.RESEND_API_KEY;
const resendFromEmail = process.env.RESEND_FROM_EMAIL || "MIVA Corp <contact@mivacorp.vn>";
const adminNotificationEmail = process.env.ADMIN_NOTIFICATION_EMAIL || "mivacorp.vn@gmail.com";

const isKeyUsable =
  typeof resendApiKey === "string" &&
  resendApiKey.trim().length > 0 &&
  !resendApiKey.includes("your_api_key") &&
  !resendApiKey.includes("khoá") &&
  !/[^\x20-\x7E]/.test(resendApiKey);

const resendClient = isKeyUsable ? new Resend(resendApiKey) : null;

/**
 * True khi chưa cấu hình RESEND_API_KEY thật (môi trường dev/thử nghiệm)
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
  if (isEarlyAccessEmailSimulated()) {
    console.log(
      `[Resend Simulation] No RESEND_API_KEY configured. Early access registration logged for project/company:`,
      data.projectName || data.company
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
    // 1. Gửi email thông báo cho Ban Quản Trị MIVA Corp
    if (adminNotificationEmail) {
      const adminHtml = generateAdminNotificationEmail(data);
      const segmentLabel = data.userSegment || "Early Access";
      const adminRes = await resendClient!.emails.send({
        from: resendFromEmail,
        to: [adminNotificationEmail],
        subject: `🔥 [Lead Mới - ${segmentLabel}] ${data.email} vừa đăng ký COSA OS`,
        html: adminHtml,
      });

      if (adminRes.error) {
        console.error("[Resend Admin Email Error]:", adminRes.error.name);
      } else {
        adminEmailSent = true;
        providerMessageId = adminRes.data?.id;
      }
    }

    // 2. Gửi email cho người dùng (nếu cấu hình bật gửi email ngay)
    const sendUserEmailNow = process.env.SEND_USER_CONFIRMATION_EMAIL === "true";
    if (sendUserEmailNow) {
      const userHtml = generateUserConfirmationEmail(data);
      const userRes = await resendClient!.emails.send({
        from: resendFromEmail,
        to: [data.email],
        subject: `[COSA OS] Xác nhận Danh sách Trải Nghiệm Sớm (Gói Free 1 Workspace · 1 Project)`,
        html: userHtml,
      });

      if (userRes.error) {
        console.warn("[Resend User Email Notice]:", userRes.error.name);
        userEmailSent = adminEmailSent;
      } else {
        userEmailSent = true;
        if (!providerMessageId) providerMessageId = userRes.data?.id;
      }
    } else {
      userEmailSent = true;
      if (!providerMessageId) providerMessageId = `lead-${Date.now()}`;
    }

    return {
      userEmailSent,
      adminEmailSent,
      providerMessageId,
    };
  } catch (error: unknown) {
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
  const fullName = escapeHtml(data.fullName);
  const company = escapeHtml(data.projectName || data.company);
  const userSegment = escapeHtml(data.userSegment || "Cá nhân / OPC");
  const email = escapeHtml(data.email);
  const phone = escapeHtml(data.phone);
  const priorityInterest = escapeHtml(data.priorityInterest);
  const registeredAt = escapeHtml(data.registeredAt);
  const surveyUrl = data.surveyUrl ? escapeHtml(data.surveyUrl) : "https://cosa.mivacorp.vn/#features";

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
                      The AI Operating System for Autonomous Ventures
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
                Bạn đã được ghi nhận trong danh sách Trải Nghiệm Sớm!
              </h1>
              
              <p style="margin: 0 0 20px; font-size: 15px; color: #cbd5e1; line-height: 1.6;">
                Cảm ơn bạn đã quan tâm đến hệ điều hành doanh nghiệp AI <strong>COSA OS</strong>. Dù bạn là học sinh, sinh viên nghiên cứu, Solo Founder hay doanh nghiệp, chúng tôi rất vinh dự được đồng hành cùng bạn.
              </p>

              <!-- Free Tier Condition Box -->
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #070c18; border-left: 4px solid #10b981; border-radius: 10px; margin-bottom: 24px; border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b;">
                <tr>
                  <td style="padding: 18px 22px;">
                    <p style="margin: 0 0 6px; font-size: 12px; font-family: monospace; font-weight: 700; color: #10b981; text-transform: uppercase;">
                      ✨ ĐẶC QUYỀN GÓI MIỄN PHÍ (FREE DISCOVERY TIER)
                    </p>
                    <p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.5;">
                      • Miễn phí 100% 0đ trọn đời giai đoạn phân tích dự án &amp; người dùng.<br>
                      • <strong>Điều kiện cấp phát:</strong> Tối đa <strong>01 Không gian làm việc (Workspace)</strong> &amp; <strong>01 Dự án (Project)</strong>.<br>
                      • Trọn bộ 6 Chuyên viên AI cộng sự hỗ trợ lập kế hoạch PRD và chiến lược 12 tuần.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Registration Summary -->
              <h3 style="margin: 0 0 14px; font-size: 14px; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">
                Thông Tin Đăng Ký Của Bạn:
              </h3>
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #070c18; border-radius: 8px; margin-bottom: 28px; font-size: 13px;">
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; width: 40%;">Dự án / Đơn vị:</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #ffffff; font-weight: 600;">${company}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8;">Nhóm đối tượng:</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #00f0ff;">${userSegment}</td>
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
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8;">Thời gian ghi nhận:</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8;">${registeredAt}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; color: #94a3b8;">Gói kích hoạt:</td>
                  <td style="padding: 12px 16px; color: #10b981; font-weight: 600;">${priorityInterest}</td>
                </tr>
              </table>

              <!-- What to expect -->
              <h3 style="margin: 0 0 12px; font-size: 14px; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">
                Bước Tiếp Theo Là Gì?
              </h3>
              <p style="margin: 0 0 20px; font-size: 14px; color: #cbd5e1; line-height: 1.6;">
                Bạn không cần phải lưu mã code hay làm thêm thủ tục gì. Khi hệ thống chính thức mở cổng đợt 1, bạn sẽ nhận được một đường <strong>Magic Link (1 chạm)</strong> gửi về email này để kích hoạt không gian làm việc ngay lập tức.
              </p>

              <div style="text-align: center; padding-top: 10px; margin-bottom: 20px;">
                <a href="${surveyUrl}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(90deg, #00f0ff, #0072ff); color: #070c18; font-weight: 700; font-size: 14px; text-decoration: none; border-radius: 10px; box-shadow: 0 4px 20px rgba(0, 240, 255, 0.4);">
                  Khám Phá &amp; Thiết Lập Blueprint Dự Án
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px; background-color: #070c18; border-top: 1px solid #1e293b; text-align: center; font-size: 12px; color: #64748b;">
              <p style="margin: 0 0 6px;">COSA OS · Create. Operate. Scale. Automate.</p>
              <p style="margin: 0;">Kiến trúc Hybrid PostgreSQL Local + Control Plane · On-Premise Data Sovereignty</p>
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
  const fullName = escapeHtml(data.fullName);
  const company = escapeHtml(data.projectName || data.company);
  const userSegment = escapeHtml(data.userSegment || "Chưa phân loại");
  const email = escapeHtml(data.email);
  const phone = escapeHtml(data.phone);
  const role = escapeHtml(data.role || "Chưa cung cấp");
  const priorityInterest = escapeHtml(data.priorityInterest);
  const note = escapeHtml(data.note || "Không có");
  const accessCode = escapeHtml(data.accessCode);
  const registeredAt = escapeHtml(data.registeredAt);

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
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Nhóm đối tượng:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee; color: #0284c7;"><strong>${userSegment}</strong></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Dự án / Công ty:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${company}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Email:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;"><a href="mailto:${mailtoHref}">${email}</a></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Số điện thoại:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;"><a href="tel:${telHref}">${phone}</a></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Chức danh / Vai trò:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${role}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Nhu cầu trọng tâm:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee; color: #0284c7;"><strong>${priorityInterest}</strong></td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Ghi chú / Nguồn:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">${note}</td></tr>
    </table>
    <p style="margin-top: 20px; font-size: 12px; color: #64748b;">Hệ thống thông báo tự động từ COSA OS Landing via Resend API.</p>
  </div>
</body>
</html>
  `;
}

/**
 * Template Email Magic Link khi phát hành chính thức (Launch Day)
 */
export function generateLaunchActivationEmail(data: {
  fullName: string;
  email: string;
  userSegment?: string;
  projectName?: string;
  activationUrl: string;
}): string {
  const fullName = escapeHtml(data.fullName);
  const segment = escapeHtml(data.userSegment || "Doanh nghiệp một người (OPC)");
  const project = escapeHtml(data.projectName || "Dự án của bạn");
  const email = escapeHtml(data.email);
  const activationUrl = escapeHtml(data.activationUrl);

  return `
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>COSA OS - Kích Hoạt Không Gian Làm Việc Của Bạn</title>
</head>
<body style="margin: 0; padding: 0; background-color: #070c18; font-family: sans-serif; color: #e2e8f0;">
  <div style="max-width: 600px; margin: 40px auto; background-color: #0d172a; border-radius: 16px; border: 1px solid #1e293b; padding: 36px 40px;">
    <h1 style="color: #ffffff; font-size: 24px; margin-top: 0;">🚀 Cổng COSA OS Đã Mở!</h1>
    <p style="font-size: 15px; color: #cbd5e1; line-height: 1.6;">
      Xin chào <strong>${fullName}</strong>, thời khắc chuyển đổi sang mô hình vận hành tự trị với AI đã tới! Cổng trải nghiệm sớm COSA OS Đợt 1 chính thức được kích hoạt cho tài khoản của bạn.
    </p>
    
    <div style="background-color: #070c18; border: 1px solid #10b981; border-radius: 12px; padding: 20px; margin: 24px 0;">
      <p style="margin: 0 0 8px; color: #10b981; font-weight: 700; font-size: 14px;">TÀI NGUYÊN ĐÃ CẤU HÌNH SẴN CHO BẠN:</p>
      <p style="margin: 4px 0; color: #cbd5e1;">• Nhóm: <strong>${segment}</strong></p>
      <p style="margin: 4px 0; color: #cbd5e1;">• Dự án khởi tạo: <strong>${project}</strong></p>
      <p style="margin: 4px 0; color: #cbd5e1;">• Hạn ngạch Gói Free: <strong>Tối đa 01 Workspace · 01 Project</strong> (Miễn phí trọn đời)</p>
      <p style="margin: 4px 0; color: #cbd5e1;">• AI Workforce: 6 Chuyên viên AI cộng sự sẵn sàng hỗ trợ</p>
    </div>

    <p style="font-size: 14px; color: #cbd5e1; margin-bottom: 28px;">
      Bạn không cần tạo tài khoản lại từ đầu. Chỉ cần bấm vào nút bên dưới để tạo mật khẩu đăng nhập và truy cập thẳng vào Workspace:
    </p>

    <div style="text-align: center; margin: 30px 0;">
      <a href="${activationUrl}" style="background: linear-gradient(90deg, #00f0ff, #38bdf8); color: #070c18; padding: 16px 36px; border-radius: 10px; font-weight: 800; font-size: 16px; text-decoration: none; display: inline-block;">
        KÍCH HOẠT WORKSPACE CỦA BẠN (1-CLICK)
      </a>
      <p style="color: #64748b; font-size: 12px; margin-top: 10px;">Link kích hoạt an toàn có thời hạn trong 48 giờ dành riêng cho ${email}</p>
    </div>
  </div>
</body>
</html>
  `;
}

