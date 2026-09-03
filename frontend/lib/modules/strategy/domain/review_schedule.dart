/// Resolve lịch buổi review hằng tuần của một vòng kickoff thành danh sách
/// datetime cụ thể — dùng để hiển thị "Thứ Sáu 11/09 & 18/09, 16:00" thay vì
/// chỉ "Thứ Sáu". Thuần, không phụ thuộc Flutter/GetX để test được.
class ReviewSchedule {
  const ReviewSchedule(this.occurrences);

  final List<DateTime> occurrences;

  static ReviewSchedule resolve({
    required DateTime roundStart,
    required int weekday,
    required String time,
    required int durationWeeks,
    int minGapDays = 3,
  }) {
    final (h, m) = _parseTime(time);
    final startDay = DateTime(
      roundStart.year,
      roundStart.month,
      roundStart.day,
    );
    final earliest = startDay.add(Duration(days: minGapDays));

    // Ngày đầu tiên >= earliest có đúng weekday.
    var firstDay = earliest;
    while (firstDay.weekday != weekday) {
      firstDay = firstDay.add(const Duration(days: 1));
    }

    final targetDay = startDay.add(Duration(days: durationWeeks * 7));
    final out = <DateTime>[];
    var cursor = firstDay;
    while (out.isEmpty || !cursor.isAfter(targetDay)) {
      out.add(DateTime(cursor.year, cursor.month, cursor.day, h, m));
      cursor = cursor.add(const Duration(days: 7));
    }
    return ReviewSchedule(out);
  }

  static (int, int) _parseTime(String time) {
    final match = RegExp(
      r'^([01]?\d|2[0-3]):([0-5]\d)$',
    ).firstMatch(time.trim());
    if (match == null) return (0, 0);
    return (int.parse(match.group(1)!), int.parse(match.group(2)!));
  }
}
