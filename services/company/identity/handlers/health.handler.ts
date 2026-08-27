import { api } from "encore.dev/api";
import { checkHealth, HealthResponse } from "../services/health.service";

export { HealthResponse };

// Endpoint kiểm tra sức khỏe ứng dụng — không yêu cầu xác thực, được sử dụng bởi
// load balancer và monitoring. Trả về trạng thái kết nối database để xác nhận
// ứng dụng hoạt động bình thường.
export const healthz = api(
  { method: "GET", path: "/healthz", expose: true, auth: false },
  async (): Promise<HealthResponse> => {
    return checkHealth();
  }
);
