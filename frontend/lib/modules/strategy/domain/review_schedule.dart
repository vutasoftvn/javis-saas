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
    // Chặn vòng lặp vô hạn khi weekday nằm ngoài 1..7 (DateTime.weekday) — nếu
    // không, `while (firstDay.weekday != weekday)` không bao giờ khớp.
    assert(
      weekday >= 1 && weekday <= 7,
      'weekday must be 1..7 (DateTime.weekday)',
    );
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
    // Dựng từng buổi theo lịch (firstDay.day + 7*k) thay vì cộng dồn
    // Duration(days: 7) trên DateTime local — qua mốc lùi giờ DST, 7 ngày tuyệt
    // đối là 168 giờ chứ không phải một tuần lịch, khiến `.day` lệch. Dart tự
    // chuẩn hoá phần ngày bị tràn tháng.
    for (var k = 0; ; k++) {
      final occ = DateTime(
        firstDay.year,
        firstDay.month,
        firstDay.day + 7 * k,
        h,
        m,
      );
      final occDay = DateTime(occ.year, occ.month, occ.day);
      // Luôn phát buổi k = 0 (đảm bảo tối thiểu 1 buổi); các buổi sau chỉ nhận
      // khi phần ngày còn <= targetDay.
      if (k > 0 && occDay.isAfter(targetDay)) break;
      out.add(occ);
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
