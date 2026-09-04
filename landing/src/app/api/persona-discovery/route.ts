import { NextRequest, NextResponse } from "next/server";
import { ZodError } from "zod";
import { parsePersonaDiscovery } from "@/lib/early-access";
import { earlyAccessStore } from "@/lib/early-access-store";

const MAX_BODY_BYTES = 16 * 1024;

export async function POST(req: NextRequest) {
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
    input = parsePersonaDiscovery(parsedBody);
  } catch (error: unknown) {
    if (error instanceof ZodError) {
      return NextResponse.json(
        { success: false, error: "Thông tin khảo sát không hợp lệ. Vui lòng kiểm tra lại." },
        { status: 400 }
      );
    }
    return NextResponse.json({ success: false, error: "Lỗi dữ liệu." }, { status: 400 });
  }

  try {
    const updated = await earlyAccessStore.updatePersonaDiscovery(input.email, {
      firstProjectGoal: input.firstProjectGoal,
      biggestChallenge: input.biggestChallenge,
      aiAutonomyLevel: input.aiAutonomyLevel,
      targetTimelineWeeks: input.targetTimelineWeeks,
      notes: input.notes,
      updatedAt: new Date().toISOString(),
    });

    if (!updated) {
      return NextResponse.json(
        {
          success: false,
          error: "Không tìm thấy thông tin đăng ký với email này. Vui lòng đăng ký trải nghiệm sớm trước.",
        },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Đã lưu bản thiết kế chân dung & nhu cầu dự án thành công!",
    });
  } catch (error: unknown) {
    console.error("[Persona Discovery API Error]:", error instanceof Error ? error.message : "unknown");
    return NextResponse.json(
      { success: false, error: "Đã có lỗi xảy ra trong quá trình lưu bản thiết kế. Vui lòng thử lại sau." },
      { status: 500 }
    );
  }
}
