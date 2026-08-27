import { createDrizzleClient, DEFAULT_COSA_DB_URL } from "../storage/client";

export interface HealthResponse {
  app: string;
  status: "ok" | "error";
  version: string;
}

// Kiểm tra kết nối database bằng SELECT 1 để xác nhận hệ thống sẵn sàng
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const db = createDrizzleClient(process.env.COSA_DATABASE_URL || DEFAULT_COSA_DB_URL);

    // Thực hiện một truy vấn đơn giản để kiểm tra kết nối DB
    const result = await db.execute(db.raw("SELECT 1"));

    return {
      app: "cosa",
      status: "ok",
      version: process.env.APP_VERSION || "unknown",
    };
  } catch (error) {
    return {
      app: "cosa",
      status: "error",
      version: process.env.APP_VERSION || "unknown",
    };
  }
}
