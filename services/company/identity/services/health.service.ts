import { createDrizzleClient, DEFAULT_COMPANY_DB_URL } from "../../shared/db/client";

export interface HealthResponse {
  app: string;
  status: "ok" | "error";
  version: string;
}

// Kiểm tra kết nối database bằng SELECT 1 để xác nhận hệ thống sẵn sàng
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const db = createDrizzleClient(process.env.COMPANY_DATABASE_URL || DEFAULT_COMPANY_DB_URL);

    // Thực hiện một truy vấn đơn giản để kiểm tra kết nối DB
    const result = await db.execute(db.raw("SELECT 1"));

    return {
      app: "company",
      status: "ok",
      version: process.env.APP_VERSION || "unknown",
    };
  } catch (error) {
    return {
      app: "company",
      status: "error",
      version: process.env.APP_VERSION || "unknown",
    };
  }
}
