/// Task 10 — token responsive DUY NHẤT cho toàn bộ workspace UI.
///
/// Trước task này, mỗi view tự đặt ngưỡng width riêng theo cảm tính
/// (900/950/1400...), khiến cùng một kích thước màn hình có thể bị coi là
/// "desktop" ở view này nhưng "mobile" ở view khác. `layoutForWidth` là
/// nguồn sự thật duy nhất cho 3 bậc layout — mọi màn hình được migrate bởi
/// plan này phải đọc breakpoint qua đây, không tự so sánh `width` trực tiếp.
enum AppLayout { compact, medium, expanded }

/// Ngưỡng: compact < 600, medium < 1024, còn lại là expanded.
/// Khớp chính xác 3 bậc trong brief Task 10 — không tự thêm bậc trung gian.
AppLayout layoutForWidth(double width) => switch (width) {
  < 600 => AppLayout.compact,
  < 1024 => AppLayout.medium,
  _ => AppLayout.expanded,
};
