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

  testWidgets('uses icon-only actions when the available width is narrow', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 800,
            child: MediaQuery(
              data: const MediaQueryData(size: Size(800, 1200)),
              child: MivaHologramCore(
                onTalkPressed: () {},
                onDashboardPressed: () {},
                onConversationModePressed: () {},
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text('COSA'), findsOneWidget);
    expect(find.text('HỘI THOẠI'), findsNothing);
    expect(find.text('ĐIỀU KHIỂN'), findsNothing);
    expect(find.byIcon(Icons.mic), findsOneWidget);
    expect(find.byIcon(Icons.record_voice_over), findsOneWidget);
  });

  testWidgets('keeps action labels on a landscape tablet', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1024, 768));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1024,
            child: MivaHologramCore(
              onTalkPressed: () {},
              onDashboardPressed: () {},
              onConversationModePressed: () {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('COSA'), findsNWidgets(2));
    expect(find.text('HỘI THOẠI'), findsOneWidget);
    expect(find.text('ĐIỀU KHIỂN'), findsOneWidget);
  });
}
