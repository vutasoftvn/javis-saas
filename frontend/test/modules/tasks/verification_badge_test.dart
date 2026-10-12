import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/data/models/verification_report_model.dart';
import 'package:frontend/modules/tasks/views/widgets/verification_badge.dart';
import 'package:get/get.dart';

VerificationReportModel _report(VerificationVerdict v, {List<VerificationCriterion>? criteria}) =>
    VerificationReportModel(
      reportId: 'vr',
      taskId: 't1',
      runId: 'r1',
      verdict: v,
      mode: 'deterministic',
      criteria: criteria ??
          const [
            VerificationCriterion(
                id: 'c1', required: true, check: 'deterministic', verdict: 'fail', reason: 'artifact_not_found'),
            VerificationCriterion(
                id: 'c2', required: false, check: 'deterministic', verdict: 'pass', reason: ''),
          ],
    );

Widget _host(Widget child) => GetMaterialApp(
      translations: AppTranslations(),
      locale: const Locale('vi', 'VN'),
      fallbackLocale: const Locale('vi', 'VN'),
      home: Scaffold(body: Center(child: child)),
    );

void main() {
  setUp(Get.reset);

  for (final c in [
    (VerificationVerdict.pass, 'Đã kiểm', const Color(0xFF10B981)),
    (VerificationVerdict.fail, 'Không đạt', const Color(0xFFEF4444)),
    (VerificationVerdict.inconclusive, 'Chưa kết luận', const Color(0xFFF59E0B)),
  ]) {
    testWidgets('verdict ${c.$1.name} hiển thị nhãn và màu đúng', (tester) async {
      await tester.pumpWidget(_host(VerificationBadge(report: _report(c.$1))));
      final text = tester.widget<Text>(find.text(c.$2));
      expect(text.style?.color, c.$3);
      expect(text.style?.fontSize, 9.5);
    });
  }

  testWidgets('chạm mở sheet liệt kê đúng số tiêu chí, chỉ hiển thị mã', (tester) async {
    await tester.pumpWidget(_host(VerificationBadge(report: _report(VerificationVerdict.fail))));
    await tester.tap(find.text('Không đạt'));
    await tester.pumpAndSettle();

    expect(find.byType(ListTile), findsNWidgets(2));
    expect(find.text('c1'), findsOneWidget);
    expect(find.textContaining('artifact_not_found'), findsOneWidget);
    expect(find.textContaining('Bắt buộc'), findsOneWidget);
    expect(find.textContaining('Tùy chọn'), findsOneWidget);
  });

  testWidgets('báo cáo không có tiêu chí vẫn hiển thị an toàn', (tester) async {
    await tester.pumpWidget(
      _host(VerificationBadge(report: _report(VerificationVerdict.inconclusive, criteria: const []))),
    );
    await tester.tap(find.text('Chưa kết luận'));
    await tester.pumpAndSettle();

    expect(find.byType(ListTile), findsNothing);
    expect(find.text('Không có tiêu chí'), findsOneWidget);
  });
}
