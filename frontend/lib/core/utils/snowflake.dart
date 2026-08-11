/// Tiện ích xử lý Snowflake ID 64-bit trên Client Flutter/Dart.
class SnowflakeUtils {
  // Epoch tùy chỉnh: 2026-01-01 00:00:00 UTC (1767225600000 ms)
  static const int customEpoch = 1767225600000;
  static const int timestampShift = 22;
  static const int nodeIdShift = 12;
  static const int maxSequence = 4095;
  static const int maxNodeId = 1023;

  /// Kiểm tra xem một chuỗi ID có phải định dạng Snowflake ID hợp lệ không.
  static bool isValidSnowflake(String? id) {
    if (id == null || id.isEmpty) return false;
    final parsed = BigInt.tryParse(id);
    return parsed != null && parsed > BigInt.zero;
  }

  /// Trích xuất thời điểm tạo (DateTime UTC) từ chuỗi Snowflake ID.
  static DateTime? parseDateTime(String? id) {
    if (!isValidSnowflake(id)) return null;
    try {
      final bigId = BigInt.parse(id!);
      final timestampMs = (bigId >> timestampShift).toInt() + customEpoch;
      return DateTime.fromMillisecondsSinceEpoch(timestampMs, isUtc: true);
    } catch (_) {
      return null;
    }
  }

  /// Trích xuất Node/Worker ID từ chuỗi Snowflake ID.
  static int? parseNodeId(String? id) {
    if (!isValidSnowflake(id)) return null;
    try {
      final bigId = BigInt.parse(id!);
      return ((bigId >> nodeIdShift) & BigInt.from(maxNodeId)).toInt();
    } catch (_) {
      return null;
    }
  }

  /// Tính khoảng thời gian đã trôi qua kể từ khi ID được tạo ra.
  static Duration? getAge(String? id) {
    final dt = parseDateTime(id);
    if (dt == null) return null;
    return DateTime.now().toUtc().difference(dt);
  }
}
