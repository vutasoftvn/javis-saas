import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/domain/review_schedule.dart';

void main() {
  test('vòng 2 tuần, bắt đầu Thứ Hai, review Thứ Sáu -> 2 buổi', () {
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 7), // Monday
      weekday: DateTime.friday, // 5
      time: '16:00',
      durationWeeks: 2,
    );
    expect(s.occurrences.length, 2);
    expect(s.occurrences.first, DateTime(2026, 9, 11, 16, 0));
    expect(s.occurrences[1], DateTime(2026, 9, 18, 16, 0));
  });

  test('minGap loại buổi review ngay hôm sau mốc bắt đầu', () {
    // roundStart Thứ Năm, review Thứ Sáu -> buổi đầu bị đẩy sang Thứ Sáu tuần sau
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 10), // Thursday
      weekday: DateTime.friday,
      time: '09:00',
      durationWeeks: 2,
    );
    expect(s.occurrences.first, DateTime(2026, 9, 18, 9, 0));
  });

  test('vòng 1 tuần -> 1 buổi', () {
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 7),
      weekday: DateTime.friday,
      time: '16:00',
      durationWeeks: 1,
    );
    expect(s.occurrences.length, 1);
    expect(s.occurrences.first, DateTime(2026, 9, 11, 16, 0));
  });

  test('time không hợp lệ -> mặc định 00:00 (không ném)', () {
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 7),
      weekday: DateTime.friday,
      time: 'oops',
      durationWeeks: 1,
    );
    expect(s.occurrences.first, DateTime(2026, 9, 11, 0, 0));
  });
}
