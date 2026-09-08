// NOTE (Task 8 — 2026-09-08): `ProjectionCache`
// (frontend/lib/modules/hologram_hub/cache/projection_cache.dart) là stub
// hoàn toàn chưa triển khai:
//   - `saveProjection()` là no-op (thân hàm chỉ có comment, không ghi gì).
//   - `getProjection()` luôn `return null`.
//   - `isCursorGap()` luôn `return false`.
// Không có backing store nào (không sqflite/Isar/Hive trong pubspec.yaml,
// grep xác nhận `ProjectionCache` không được import/dùng ở bất kỳ đâu khác
// trong `frontend/lib`). Vì vậy 3 test case gốc (lưu/đọc projection từ local
// DB, phát hiện cursor gap, tự phục hồi khi DB bị xoá) đều mô tả hành vi
// CHƯA TỒN TẠI trong code — viết assertion cho các case này sẽ chỉ kiểm tra
// giá trị hard-code (luôn null/luôn false), không phản ánh logic thật nào.
// Theo nguyên tắc Task 8 ("xoá test name nếu feature chưa tồn tại thay vì
// giữ test xanh rỗng"), toàn bộ 3 test case đã bị xoá khỏi file này thay vì
// giữ placeholder — xem task-8-report.md để biết chi tiết đã kiểm tra gì.
//
// Khi `ProjectionCache` được triển khai thật (persistence + cursor-gap
// detection), viết lại test file này với assertion thật trên hành vi đó.

void main() {}
