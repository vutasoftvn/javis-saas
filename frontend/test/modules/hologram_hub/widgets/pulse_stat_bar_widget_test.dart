import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/data/models/company_pulse_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart';

void main() {
  testWidgets('renders all 4 pulse stat labels and values in Vietnamese', (tester) async {
    final pulse = CompanyPulseModel(
      goalsOnTrack: 3,
      totalActiveGoals: 5,
      activeMissions: 2,
      needsDecisionCount: 1,
      majorRisksCount: 0,
      updatedAt: DateTime.utc(2026, 9, 4),
    );

    await tester.pumpWidget(
      GetMaterialApp(
        translations: AppTranslations(),
        locale: const Locale('vi', 'VN'),
        home: Scaffold(body: PulseStatBarWidget(pulse: pulse)),
      ),
    );

    expect(find.text('3/5'), findsOneWidget);
    expect(find.text('Mục tiêu đúng hạn'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('Missions đang chạy'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);
    expect(find.text('Quyết định cần chốt'), findsOneWidget);
    expect(find.text('0'), findsOneWidget);
    expect(find.text('Rủi ro cần lưu ý'), findsOneWidget);
  });

  testWidgets('renders all 4 pulse stat labels and values in English', (tester) async {
    final pulse = CompanyPulseModel(
      goalsOnTrack: 3,
      totalActiveGoals: 5,
      activeMissions: 2,
      needsDecisionCount: 1,
      majorRisksCount: 0,
      updatedAt: DateTime.utc(2026, 9, 4),
    );

    await tester.pumpWidget(
      GetMaterialApp(
        translations: AppTranslations(),
        locale: const Locale('en', 'US'),
        home: Scaffold(body: PulseStatBarWidget(pulse: pulse)),
      ),
    );

    expect(find.text('3/5'), findsOneWidget);
    expect(find.text('Goals on track'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('Active missions'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);
    expect(find.text('Decisions needed'), findsOneWidget);
    expect(find.text('0'), findsOneWidget);
    expect(find.text('Major risks'), findsOneWidget);
  });

  testWidgets('renders zeroed stats when pulse is null', (tester) async {
    await tester.pumpWidget(
      GetMaterialApp(
        translations: AppTranslations(),
        locale: const Locale('vi', 'VN'),
        home: const Scaffold(body: PulseStatBarWidget(pulse: null)),
      ),
    );

    expect(find.text('0/0'), findsOneWidget);
  });
}
