import { createDrizzleClient, DEFAULT_COSA_DB_URL } from "../storage/client";
import { APIError } from "encore.dev/api";

export interface HealthResponse {
  app: string;
  status: "ok";
  version: string;
}

// Kiểm tra kết nối database bằng SELECT 1 để xác nhận hệ thống sẵn sàng.
// Returns HTTP 200 + {status: "ok"} nếu DB khỏe mạnh.
// Throws APIError.unavailable (HTTP 503) nếu DB không kết nối được — load
// balancer sẽ biết instance này không sẵn sàng phục vụ.
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const db = createDrizzleClient(process.env.COSA_DATABASE_URL || DEFAULT_COSA_DB_URL);

    // Thực hiện một truy vấn đơn giản để kiểm tra kết nối DB
    await db.execute(db.raw("SELECT 1"));

    return {
      app: "cosa",
      status: "ok",
      version: process.env.APP_VERSION || "unknown",
    };
  } catch (error) {
    // Trả về HTTP 503 để load balancer biết instance không sẵn sàng
    throw APIError.unavailable("database connection failed");
  }
}
