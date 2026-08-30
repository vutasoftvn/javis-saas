import { NextRequest, NextResponse } from "next/server";
import { sendEarlyAccessEmails } from "@/lib/resend";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      fullName,
      email,
      phone,
      company,
      role,
      teamSize,
      priorityInterest,
      note,
    } = body;

    // Validate các trường bắt buộc
    if (!fullName || typeof fullName !== "string" || !fullName.trim()) {
      return NextResponse.json(
        { success: false, error: "Vui lòng nhập họ và tên của bạn." },
        { status: 400 }
      );
    }

    if (!email || typeof email !== "string" || !email.includes("@")) {
      return NextResponse.json(
        { success: false, error: "Vui lòng nhập địa chỉ email hợp lệ." },
        { status: 400 }
      );
    }

    if (!phone || typeof phone !== "string" || phone.trim().length < 8) {
      return NextResponse.json(
        { success: false, error: "Vui lòng nhập số điện thoại hoặc Zalo hợp lệ." },
        { status: 400 }
      );
    }

    if (!company || typeof company !== "string" || !company.trim()) {
      return NextResponse.json(
        { success: false, error: "Vui lòng nhập tên công ty hoặc dự án." },
        { status: 400 }
      );
    }

    // Sinh mã VIP ngẫu nhiên cho Early Access Pass
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const accessCode = `COSA-VIP-${randomSuffix}`;
    const registeredAt = new Date().toLocaleString("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      dateStyle: "full",
      timeStyle: "medium",
    });

    const registrationData = {
      fullName: fullName.trim(),
      email: email.trim().toLowerCase(),
      phone: phone.trim(),
      company: company.trim(),
      role: role ? String(role).trim() : undefined,
      teamSize: teamSize ? String(teamSize).trim() : undefined,
      priorityInterest: priorityInterest || "Trọn bộ Hệ điều hành COSA OS",
      note: note ? String(note).trim() : undefined,
      accessCode,
      registeredAt,
    };

    // Gửi email qua Resend
    const emailResult = await sendEarlyAccessEmails(registrationData);

    return NextResponse.json({
      success: true,
      accessCode,
      message: "Đăng ký quyền sử dụng sớm thành công! Email xác nhận đã được gửi.",
      emailDelivery: {
        simulated: Boolean(emailResult.simulated),
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
