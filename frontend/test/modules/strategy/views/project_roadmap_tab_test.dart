import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/views/tabs/project_roadmap_tab.dart';

void main() {
  // Mốc thời gian cố định để test số ngày đã triển khai ổn định.
  final now = DateTime.utc(2026, 1, 21, 12);

  group('projectDateBadge', () {
    test('start date 10 ngày trước → badge chứa "đã triển khai 10 ngày"', () {
      final badge = projectDateBadge({
        'startDate': DateTime.utc(2026, 1, 11, 12).toIso8601String(),
      }, now: now);

      expect(badge, isNotNull);
      expect(badge, contains('đã triển khai 10 ngày'));
    });

    test(
      'có start + end date → badge giữ cả khoảng ngày lẫn "đã triển khai"',
      () {
        final badge = projectDateBadge({
          'startDate': DateTime.utc(2026, 1, 11).toIso8601String(),
          'endDate': DateTime.utc(2026, 3, 8).toIso8601String(),
        }, now: now);

        expect(badge, isNotNull);
        expect(badge, contains('11/01'));
        expect(badge, contains('08/03/2026'));
        expect(badge, contains('tuần'));
        expect(badge, contains('đã triển khai'));
      },
    );

    test('không có start date → trả null', () {
      expect(projectDateBadge({}, now: now), isNull);
      expect(projectDateBadge({'startDate': ''}, now: now), isNull);
    });

    test('key legacy snake_case start_date vẫn hoạt động (fallback)', () {
      final badge = projectDateBadge({
        'start_date': DateTime.utc(2026, 1, 11, 12).toIso8601String(),
      }, now: now);

      expect(badge, isNotNull);
      expect(badge, contains('đã triển khai 10 ngày'));
    });

    test('start date trong tương lai → không thêm hậu tố "đã triển khai"', () {
      final badge = projectDateBadge({
        'startDate': DateTime.utc(2026, 2, 1).toIso8601String(),
      }, now: now);

      expect(badge, isNotNull);
      expect(badge, isNot(contains('đã triển khai')));
    });
  });
}
