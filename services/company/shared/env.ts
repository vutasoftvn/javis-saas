// Dùng chung để phân biệt staging/production với development khi quyết định
// có cho phép fallback secret/DSN mặc định hay không (P0 fail-closed).
export function isStagingOrProd(): boolean {
  const env = (process.env.ENVIRONMENT || process.env.NODE_ENV || process.env.APP_ENV || "development").toLowerCase();
  return env === "production" || env === "staging" || env === "prod";
}
