import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/widgets/app_button.dart';

void main() {
  testWidgets('AppButton renders label and uses standard medium height 44', (WidgetTester tester) async {
    bool pressed = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppButton(
            label: 'Test Button',
            onPressed: () {
              pressed = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('Test Button'), findsOneWidget);

    final finder = find.byType(ElevatedButton);
    expect(finder, findsOneWidget);

    final ElevatedButton button = tester.widget(finder);
    final style = button.style;
    expect(style?.minimumSize?.resolve({}), equals(const Size(64, 44)));

    await tester.tap(finder);
    expect(pressed, isTrue);
  });

  testWidgets('AppButton small size uses height 36', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppButton(
            label: 'Small Button',
            size: AppButtonSize.small,
            onPressed: () {},
          ),
        ),
      ),
    );

    final finder = find.byType(ElevatedButton);
    final ElevatedButton button = tester.widget(finder);
    final style = button.style;
    expect(style?.minimumSize?.resolve({}), equals(const Size(64, 36)));
  });

  testWidgets('AppButton large size uses height 52', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppButton(
            label: 'Large Button',
            size: AppButtonSize.large,
            onPressed: () {},
          ),
        ),
      ),
    );

    final finder = find.byType(ElevatedButton);
    final ElevatedButton button = tester.widget(finder);
    final style = button.style;
    expect(style?.minimumSize?.resolve({}), equals(const Size(64, 52)));
  });
}
