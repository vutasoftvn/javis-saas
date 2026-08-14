import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/miva_hologram_core.dart';

void main() {
  testWidgets('uses the concise COSA identity and active status copy', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1800, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1800,
            child: MivaHologramCore(
              onTalkPressed: () {},
              onDashboardPressed: () {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('COSA - Hệ điều hành AI toàn diện'), findsOneWidget);
    expect(
      find.text('Suy nghĩ - Kế hoạch - Hành động - Kết quả'),
      findsOneWidget,
    );
    expect(find.text('Hoạt động'), findsNothing);
  });

  testWidgets('renders icon-only action buttons for conversation and dashboard', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1200, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1200,
            child: MivaHologramCore(
              onTalkPressed: () {},
              onDashboardPressed: () {},
              onConversationModePressed: () {},
            ),
          ),
        ),
      ),
    );

    // COSA is only in the central hologram orb text, not as an action button
    expect(find.text('COSA'), findsOneWidget);
    expect(find.text('HỘI THOẠI'), findsNothing);
    expect(find.text('ĐIỀU KHIỂN'), findsNothing);
    expect(find.byIcon(Icons.record_voice_over), findsOneWidget);
    expect(find.byIcon(Icons.dashboard_customize_outlined), findsOneWidget);
  });
}
