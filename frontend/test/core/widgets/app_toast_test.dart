import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/widgets/app_toast.dart';
import 'package:get/get.dart';

void main() {
  testWidgets('AppToast handles headless invocation safely without crashing', (tester) async {
    expect(() => AppToast.success('Test message'), returnsNormally);
    expect(() => AppToast.error('Error message'), returnsNormally);
    expect(() => AppToast.warning('Warning message'), returnsNormally);
    expect(() => AppToast.info('Info message'), returnsNormally);
  });

  testWidgets('AppToast renders in GetMaterialApp on top right', (tester) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () {
                AppToast.success(
                  'Thao tác thành công',
                  title: 'Chúc mừng',
                );
              },
              child: const Text('Show Toast'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Show Toast'));
    await tester.pump(); // Start animation
    await tester.pump(const Duration(milliseconds: 300)); // Advance animation

    expect(find.text('Thao tác thành công'), findsOneWidget);
    expect(find.text('Chúc mừng'), findsOneWidget);

    // Let the timer finish to prevent pending timer assertion
    await tester.pumpAndSettle(const Duration(seconds: 5));
  });
}
