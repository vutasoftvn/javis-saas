/// Kết quả chuẩn cho mọi endpoint "list" của Strategy module.
///
/// Trước đây `StrategyService` gộp 3 tình huống khác nhau (thành công-rỗng,
/// 404, và mọi lỗi khác — 401/403/409/5xx, JSON hỏng, mất kết nối) thành cùng
/// một `List<dynamic>` rỗng, khiến UI không thể phân biệt "chưa có dữ liệu"
/// với "gọi API thất bại". `StrategyListResult<T>` tách rõ 3 trạng thái để
/// tầng view/controller có thể hiển thị đúng: danh sách thật, banner
/// "tính năng chưa khả dụng", hoặc banner lỗi kèm nút thử lại.
final class StrategyListResult<T> {
  /// Gọi thành công, `items` là dữ liệu thật (có thể rỗng nếu backend xác
  /// nhận danh sách rỗng qua response 2xx hợp lệ).
  const StrategyListResult.success(this.items)
      : isUnavailable = false,
        errorMessage = null;

  /// Endpoint trả 404 nhưng đây là 404 "có chủ đích" — tính năng/tài nguyên
  /// được biết là optional, không phải lỗi. `items` luôn rỗng, không có
  /// thông điệp lỗi để hiển thị dạng banner đỏ.
  const StrategyListResult.unavailable()
      : items = const [],
        isUnavailable = true,
        errorMessage = null;

  /// Mọi tình huống thất bại thật: 401/403/409/5xx, 404 không được xác nhận
  /// là optional, JSON hỏng, hoặc lỗi transport (mất mạng, timeout...).
  /// `errorMessage` luôn có nội dung để UI hiển thị banner lỗi + nút thử lại.
  const StrategyListResult.failure(this.errorMessage)
      : items = const [],
        isUnavailable = false;

  final List<T> items;
  final bool isUnavailable;
  final String? errorMessage;

  /// `true` khi có lỗi thật cần hiển thị (không tính trường hợp `unavailable`
  /// — đó là trạng thái hợp lệ, không phải lỗi).
  bool get isFailure => errorMessage != null;
}
