import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { ZodError } from "zod";
import { isProductionEnvironment, parseEarlyAccessRegistration, verifyTurnstileToken } from "@/lib/early-access";
import { isEarlyAccessEmailSimulated, sendEarlyAccessEmails } from "@/lib/resend";
import { earlyAccessStore } from "@/lib/early-access-store";
import { earlyAccessRateLimiter } from "@/lib/early-access-rate-limit";

// Giới hạn dung lượng body: chặn payload quá khổ trước khi JSON.parse (tránh
// tốn CPU parse chuỗi lớn) — 16 KiB đủ rộng cho toàn bộ form đăng ký hợp lệ.
const MAX_BODY_BYTES = 16 * 1024;

// 3 lượt thử được chấp nhận (đã qua honeypot + CAPTCHA)/IP/giờ — chặn brute
// force/spam từ một nguồn duy nhất mà không chặn nhầm người dùng thật.
const IP_RATE_LIMIT = { limit: 3, windowSeconds: 60 * 60 };
// 1 lượt đăng ký mới/email/ngày — lớp bảo vệ bổ sung cho race condition giữa
// bước findByEmail và create (dedup chính vẫn là email UNIQUE trong store).
const EMAIL_RATE_LIMIT = { limit: 1, windowSeconds: 24 * 60 * 60 };

const GENERIC_ERROR = "Đã có lỗi xảy ra trong quá trình xử lý. Vui lòng thử lại sau.";
const RATE_LIMIT_ERROR = "Bạn đã thử quá nhiều lần. Vui lòng thử lại sau.";
const SEND_FAILURE_ERROR = "Không thể gửi email xác nhận. Vui lòng thử lại sau hoặc liên hệ trực tiếp.";
const CONCURRENT_ATTEMPT_ERROR = "Yêu cầu đang được xử lý, vui lòng thử lại sau ít phút.";
const SUCCESS_MESSAGE = "Đăng ký quyền sử dụng sớm thành công! Email xác nhận đã được gửi.";
const SIMULATED_MESSAGE =
  "Đăng ký quyền sử dụng sớm đã được ghi nhận (môi trường thử nghiệm — chưa cấu hình gửi email thật).";

// Độ trễ giả lập cho nhánh "email đã đăng ký & đã gửi/simulated từ trước"
// (idempotent-fast-path) — nhánh này vốn dĩ chỉ chạy 2 bước rẻ (rate-limit
// IP + findByEmail) trong khi nhánh đăng ký MỚI còn phải qua rate-limit
// theo email, insert DB, và gọi mạng thật tới Resend (thường mất hàng trăm
// ms). Không bù độ trễ này sẽ tạo ra một side-channel qua thời gian phản hồi
// để phân biệt "email đã tồn tại" với "email mới" — vi phạm yêu cầu không
// tiết lộ trạng thái đăng ký của một địa chỉ email. Có thể tinh chỉnh qua
// biến môi trường để khớp độ trễ thực tế của Resend trên từng hạ tầng.
const DUPLICATE_RESPONSE_PADDING_MS = Number(process.env.EARLY_ACCESS_DUPLICATE_LATENCY_MS ?? 300);

async function padDuplicateResponseLatency(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, DUPLICATE_RESPONSE_PADDING_MS));
}

function successResponse(
  accessCode: string,
  delivery: { simulated: boolean; userEmailSent: boolean; adminEmailSent: boolean }
) {
  return NextResponse.json({
    success: true,
    accessCode,
    message: SUCCESS_MESSAGE,
    emailDelivery: delivery,
  });
}

function simulatedResponse(accessCode: string) {
  // KHÔNG trả success: true ở nhánh này — chưa có email thật nào được gửi,
  // nên success phải là false để caller không thể hiểu nhầm là đã gửi email
  // thành công. `simulated: true` + `message` mang thông tin trung thực về
  // trạng thái môi trường dev/chưa cấu hình.
  return NextResponse.json({
    success: false,
    simulated: true,
    accessCode,
    message: SIMULATED_MESSAGE,
    emailDelivery: { simulated: true, userEmailSent: false, adminEmailSent: false },
  });
}

function sendFailureResponse() {
  return NextResponse.json({ success: false, error: SEND_FAILURE_ERROR }, { status: 502 });
}

function formatRegisteredAt(isoTimestamp: string): string {
  return new Date(isoTimestamp).toLocaleString("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    dateStyle: "full",
    timeStyle: "medium",
  });
}

/**
 * Lấy client IP thật từ header nền tảng tin cậy. Trên Vercel và hầu hết các
 * reverse proxy biên (nginx, Cloudflare), proxy biên tự ghi đè/append IP
 * client thật vào ĐẦU danh sách x-forwarded-for trước khi chuyển tiếp tới
 * origin — khác với các header client có thể tự set tuỳ ý (vd. x-real-ip khi
 * không có proxy kiểm soát). Nếu vận hành landing sau một proxy KHÔNG loại bỏ
 * header ngoài do client gửi, IP này có thể bị giả mạo — cần cấu hình proxy
 * biên để luôn ghi đè x-forwarded-for, không nối thêm vào giá trị client gửi.
 */
function resolveClientIp(req: NextRequest): string {
  const forwardedFor = req.headers.get("x-forwarded-for");
  if (forwardedFor) {
    const first = forwardedFor.split(",")[0]?.trim();
    if (first) return first;
  }
  return "unknown";
}

function fakeSuccessResponse() {
  // Phản hồi cho honeypot bị kích hoạt (bot điền trường ẩn): trả về y hệt
  // hình dạng response thành công thật để không tiết lộ cho bot biết nó đã bị
  // phát hiện, nhưng KHÔNG lưu trữ/gửi email nào thật sự xảy ra.
  return NextResponse.json({
    success: true,
    accessCode: randomUUID(),
    message: "Đăng ký quyền sử dụng sớm thành công! Email xác nhận đã được gửi.",
    emailDelivery: { simulated: false, userEmailSent: true, adminEmailSent: true },
  });
}

export async function POST(req: NextRequest) {
  // Đọc body dưới dạng text trước để có thể kiểm tra kích thước byte thực tế
  // (đúng theo UTF-8) trước khi parse JSON — chặn HTTP 413 sớm, không tốn
  // công JSON.parse trên payload quá khổ.
  const rawBody = await req.text();
  if (Buffer.byteLength(rawBody, "utf8") > MAX_BODY_BYTES) {
    return NextResponse.json(
      { success: false, error: "Yêu cầu vượt quá giới hạn kích thước cho phép." },
      { status: 413 }
    );
  }

  let parsedBody: unknown;
  try {
    parsedBody = JSON.parse(rawBody);
  } catch {
    return NextResponse.json(
      { success: false, error: "Dữ liệu gửi lên không đúng định dạng JSON." },
      { status: 400 }
    );
  }

  let input;
  try {
    input = parseEarlyAccessRegistration(parsedBody);
  } catch (error: unknown) {
    if (error instanceof ZodError) {
      return NextResponse.json(
        { success: false, error: "Thông tin đăng ký không hợp lệ. Vui lòng kiểm tra lại các trường." },
        { status: 400 }
      );
    }
    throw error;
  }

  // Honeypot: người dùng thật không bao giờ điền trường ẩn này.
  if (input.website && input.website.length > 0) {
    return fakeSuccessResponse();
  }

  const clientIp = resolveClientIp(req);

  try {
    // Bước 2 (bắt buộc theo brief): xác thực chống bot TRƯỚC khi chạm tới
    // persistence/email — CAPTCHA chỉ bắt buộc ở production để dev/test không
    // cần hạ tầng Turnstile thật.
    if (isProductionEnvironment()) {
      const captchaValid = await verifyTurnstileToken(input.turnstileToken, clientIp);
      if (!captchaValid) {
        return NextResponse.json(
          { success: false, error: "Xác minh chống spam không hợp lệ. Vui lòng thử lại." },
          { status: 400 }
        );
      }
    }

    const ipQuota = await earlyAccessRateLimiter.consume(
      `ip:${clientIp}`,
      IP_RATE_LIMIT.limit,
      IP_RATE_LIMIT.windowSeconds
    );
    if (!ipQuota.allowed) {
      return NextResponse.json(
        { success: false, error: RATE_LIMIT_ERROR },
        { status: 429, headers: { "Retry-After": String(ipQuota.retryAfterSeconds) } }
      );
    }

    // Bước 3: persist trước, queue/gửi email sau — dedup theo email đã
    // normalize (lowercase/trim ở schema). Idempotent CHỈ khi lần đăng ký
    // trước đó thực sự đã gửi/queue email thành công (queued) hoặc đã ghi
    // nhận đúng trạng thái simulated — trả về đúng hình dạng response thành
    // công như một đăng ký mới, KHÔNG gửi lại email và KHÔNG để lộ qua
    // status/hình dạng response rằng đây là một địa chỉ đã đăng ký từ trước.
    const existing = await earlyAccessStore.findByEmail(input.email);
    if (existing) {
      if (existing.emailDeliveryStatus === "queued" || existing.emailDeliveryStatus === "simulated") {
        await padDuplicateResponseLatency();
        return successResponse(existing.accessCode, {
          simulated: existing.emailDeliveryStatus === "simulated",
          userEmailSent: existing.emailDeliveryStatus === "queued",
          adminEmailSent: existing.emailDeliveryStatus === "queued",
        });
      }

      // Trạng thái "pending"/"failed": lần đăng ký trước đó CHƯA từng gửi
      // email thành công (ví dụ crash giữa chừng, hoặc lần gửi trước lỗi
      // 502) — không được trả success: true chỉ vì bản ghi đã tồn tại. Thử
      // gửi lại ngay tại đây; độ trễ mạng thật của lần thử lại này cũng tự
      // nhiên giảm chênh lệch thời gian so với nhánh đăng ký mới, không cần
      // độ trễ giả lập bổ sung.
      //
      // TRƯỚC KHI gửi, phải claim quyền gửi một cách NGUYÊN TỬ
      // (claimEmailAttempt): nếu 2 request gần như đồng thời (double-click,
      // retry storm) cùng đọc thấy "pending"/"failed" ở findByEmail phía
      // trên, không có bước claim này thì CẢ HAI sẽ cùng gọi
      // sendEarlyAccessEmails và người dùng nhận 2+ email xác nhận trùng
      // lặp. claimEmailAttempt() đảm bảo chỉ request thắng cuộc (chuyển được
      // pending/failed -> sending) mới được gọi provider; request thua thấy
      // claim thất bại và trả về ngay, không gửi gì thêm.
      const claimed = await earlyAccessStore.claimEmailAttempt(existing.id);
      if (!claimed) {
        return NextResponse.json(
          { success: false, error: CONCURRENT_ATTEMPT_ERROR },
          { status: 202 }
        );
      }

      const retryResult = await sendEarlyAccessEmails({
        fullName: existing.fullName,
        email: existing.email,
        phone: existing.phone,
        company: existing.company,
        role: existing.role,
        teamSize: existing.teamSize,
        priorityInterest: existing.priorityInterest,
        note: existing.note,
        accessCode: existing.accessCode,
        registeredAt: formatRegisteredAt(existing.registeredAt),
      });

      if (retryResult.simulated) {
        // Môi trường đã chuyển sang simulated giữa các lần thử — cập nhật
        // trạng thái lưu trữ tương ứng để không kẹt ở "sending"/"pending"
        // mãi mãi và các lần resubmit sau không retry vô ích nữa.
        await earlyAccessStore.markEmailSimulated(existing.id);
        return simulatedResponse(existing.accessCode);
      }

      if (!retryResult.userEmailSent) {
        await earlyAccessStore.markEmailFailed(existing.id);
        console.error(
          "[Early Access API] Retried user email delivery failed for registration id:",
          existing.id
        );
        return sendFailureResponse();
      }

      if (retryResult.providerMessageId) {
        await earlyAccessStore.markEmailQueued(existing.id, retryResult.providerMessageId);
      }

      return successResponse(existing.accessCode, {
        simulated: false,
        userEmailSent: retryResult.userEmailSent,
        adminEmailSent: retryResult.adminEmailSent,
      });
    }

    const emailQuota = await earlyAccessRateLimiter.consume(
      `email:${input.email}`,
      EMAIL_RATE_LIMIT.limit,
      EMAIL_RATE_LIMIT.windowSeconds
    );
    if (!emailQuota.allowed) {
      return NextResponse.json(
        { success: false, error: RATE_LIMIT_ERROR },
        { status: 429, headers: { "Retry-After": String(emailQuota.retryAfterSeconds) } }
      );
    }

    // accessCode chỉ là mã tham chiếu đăng ký hiển thị cho người dùng tra
    // cứu, KHÔNG phải credential cấp quyền truy cập hệ thống.
    const accessCode = randomUUID();
    const simulated = isEarlyAccessEmailSimulated();

    const registration = await earlyAccessStore.create({
      fullName: input.fullName,
      email: input.email,
      phone: input.phone,
      company: input.company,
      role: input.role,
      teamSize: input.teamSize,
      priorityInterest: input.priorityInterest || "Trọn bộ Hệ điều hành COSA OS",
      note: input.note,
      accessCode,
      // Quyết định trạng thái ban đầu TRƯỚC khi gọi sendEarlyAccessEmails —
      // đúng thứ tự "persist first" mà không cần chờ kết quả gửi email vì
      // isEarlyAccessEmailSimulated() chỉ đọc cấu hình env đồng bộ.
      emailDeliveryStatus: simulated ? "simulated" : "pending",
    });

    const emailResult = await sendEarlyAccessEmails({
      fullName: registration.fullName,
      email: registration.email,
      phone: registration.phone,
      company: registration.company,
      role: registration.role,
      teamSize: registration.teamSize,
      priorityInterest: registration.priorityInterest,
      note: registration.note,
      accessCode: registration.accessCode,
      registeredAt: formatRegisteredAt(registration.registeredAt),
    });

    // Chỉ trả success: true khi email xác nhận thực sự gửi tới người dùng
    // thành công. Ở môi trường dev/chưa cấu hình RESEND_API_KEY (simulated),
    // trả rõ simulated: true và thông báo không có email nào được gửi —
    // tuyệt đối không tuyên bố "đã gửi email" khi không có email nào được
    // gửi thật.
    if (emailResult.simulated) {
      return simulatedResponse(accessCode);
    }

    if (!emailResult.userEmailSent) {
      // Ghi nhận trạng thái "failed" để lần đăng ký lại (duplicate) sau này
      // biết phải thử gửi lại thay vì âm thầm báo success: true. Không log
      // email/phone/accessCode — chỉ log id bản ghi (UUID nội bộ, không phải
      // PII) để tra cứu khi cần điều tra sự cố.
      await earlyAccessStore.markEmailFailed(registration.id);
      console.error("[Early Access API] User email delivery failed for registration id:", registration.id);
      return sendFailureResponse();
    }

    // Chỉ đánh dấu "queued" sau khi nhà cung cấp email trả về message ID thật
    // — đúng yêu cầu "chỉ markEmailQueued sau khi có provider message id".
    if (emailResult.providerMessageId) {
      await earlyAccessStore.markEmailQueued(registration.id, emailResult.providerMessageId);
    }

    return successResponse(accessCode, {
      simulated: false,
      userEmailSent: emailResult.userEmailSent,
      adminEmailSent: emailResult.adminEmailSent,
    });
  } catch (error: unknown) {
    // Không log raw body/email/phone/accessCode — chỉ log message lỗi chung
    // để phục vụ điều tra sự cố mà không rò rỉ PII vào log hệ thống.
    console.error("[Early Access API Error]:", error instanceof Error ? error.message : "unknown error");
    return NextResponse.json({ success: false, error: GENERIC_ERROR }, { status: 500 });
  }
}
