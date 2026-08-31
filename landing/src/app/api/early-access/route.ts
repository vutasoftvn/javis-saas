import { NextRequest, NextResponse } from "next/server";
import { ZodError } from "zod";
import { parseEarlyAccessRegistration } from "@/lib/early-access";
import { sendEarlyAccessEmails } from "@/lib/resend";

// Giới hạn dung lượng body: chặn payload quá khổ trước khi JSON.parse (tránh
// tốn CPU parse chuỗi lớn) — 16 KiB đủ rộng cho toàn bộ form đăng ký hợp lệ.
const MAX_BODY_BYTES = 16 * 1024;

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

  try {
    // Sinh mã VIP ngẫu nhiên cho Early Access Pass
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const accessCode = `COSA-VIP-${randomSuffix}`;
    const registeredAt = new Date().toLocaleString("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      dateStyle: "full",
      timeStyle: "medium",
    });

    const registrationData = {
      fullName: input.fullName,
      email: input.email,
      phone: input.phone,
      company: input.company,
      role: input.role,
      teamSize: input.teamSize,
      priorityInterest: input.priorityInterest || "Trọn bộ Hệ điều hành COSA OS",
      note: input.note,
      accessCode,
      registeredAt,
    };

    // Gửi email qua Resend
    const emailResult = await sendEarlyAccessEmails(registrationData);

    // Chỉ trả success: true khi email xác nhận thực sự gửi tới người dùng
    // thành công. Ở môi trường dev/chưa cấu hình RESEND_API_KEY (simulated),
    // trả rõ simulated: true và thông báo không có email nào được gửi —
    // tuyệt đối không tuyên bố "đã gửi email" khi không có email nào được
    // gửi thật.
    if (emailResult.simulated) {
      // KHÔNG trả success: true ở nhánh này — chưa có email thật nào được
      // gửi, nên success phải là false để caller không thể hiểu nhầm là đã
      // gửi email thành công. `simulated: true` + `message` mang thông tin
      // trung thực về trạng thái môi trường dev/chưa cấu hình.
      return NextResponse.json({
        success: false,
        simulated: true,
        accessCode,
        message:
          "Đăng ký quyền sử dụng sớm đã được ghi nhận (môi trường thử nghiệm — chưa cấu hình gửi email thật).",
        emailDelivery: {
          simulated: true,
          userEmailSent: false,
          adminEmailSent: false,
        },
      });
    }

    if (!emailResult.userEmailSent) {
      console.error("[Early Access API] User email delivery failed:", emailResult.error);
      return NextResponse.json(
        {
          success: false,
          error: "Không thể gửi email xác nhận. Vui lòng thử lại sau hoặc liên hệ trực tiếp.",
        },
        { status: 502 }
      );
    }

    return NextResponse.json({
      success: true,
      accessCode,
      message: "Đăng ký quyền sử dụng sớm thành công! Email xác nhận đã được gửi.",
      emailDelivery: {
        simulated: false,
        userEmailSent: emailResult.userEmailSent,
        adminEmailSent: emailResult.adminEmailSent,
      },
    });
  } catch (error: unknown) {
    console.error("[Early Access API Error]:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Đã có lỗi xảy ra trong quá trình xử lý. Vui lòng thử lại sau.",
      },
      { status: 500 }
    );
  }
}
