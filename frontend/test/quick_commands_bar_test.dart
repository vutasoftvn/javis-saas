import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/quick_commands_bar.dart';

void main() {
  testWidgets('shows four quick-command buttons with labels on wide layouts', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1800, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1800,
            child: QuickCommandsBar(onCommandTap: (_) {}),
          ),
        ),
      ),
    );

    expect(find.text('LỆNH NHANH'), findsNothing);
    expect(find.byIcon(Icons.today_outlined), findsOneWidget);
    expect(find.byIcon(Icons.track_changes), findsOneWidget);
    expect(find.byIcon(Icons.bolt), findsOneWidget);
    expect(find.byIcon(Icons.account_balance_wallet_outlined), findsOneWidget);
  });

  testWidgets('hides quick-command labels when the available width is narrow', (
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
              child: QuickCommandsBar(onCommandTap: (_) {}),
            ),
          ),
        ),
      ),
    );

    expect(find.text('Tổng quan hôm nay'), findsNothing);
    expect(find.text('Kiểm tra tiến độ OKRs'), findsNothing);
    expect(find.byIcon(Icons.today_outlined), findsOneWidget);
    expect(find.byIcon(Icons.track_changes), findsOneWidget);
  });


  testWidgets('keeps quick-command labels on a landscape tablet', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 768));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1024,
            child: QuickCommandsBar(onCommandTap: (_) {}),
          ),
        ),
      ),
    );

    expect(find.text('Tổng quan hôm nay'), findsOneWidget);
    expect(find.text('Báo cáo tài chính'), findsOneWidget);
  });

  testWidgets('fits command buttons at the desktop center-column width', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MediaQuery(
            data: const MediaQueryData(
              size: Size(1440, 900),
              textScaler: TextScaler.linear(1.5),
            ),
            child: SizedBox(
              width: 839.5,
              child: QuickCommandsBar(onCommandTap: (_) {}),
            ),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
  });

  testWidgets('keeps labelled commands within the 839.5px desktop rail', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Align(
            alignment: Alignment.topLeft,
            child: SizedBox(
              width: 839.5,
              child: QuickCommandsBar(onCommandTap: (_) {}),
            ),
          ),
        ),
      ),
    );

    expect(find.text('Báo cáo tài chính'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
