import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/widgets/app_modal_dialog.dart';

void main() {
  testWidgets('AppModalDialog renders title, content, and actions without errors', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () {
                AppModalDialog.show(
                  context: context,
                  title: 'Xóa Strategy Canvas',
                  subtitle: 'Hành động này sẽ xóa vĩnh viễn Canvas',
                  content: const Text('Bạn có chắc chắn muốn xóa không?'),
                  actions: [
                    TextButton(
                      onPressed: () {},
                      child: const Text('Huỷ'),
                    ),
                    ElevatedButton(
                      onPressed: () {},
                      child: const Text('Xác nhận Xóa'),
                    ),
                  ],
                );
              },
              child: const Text('Open Modal'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open Modal'));
    await tester.pumpAndSettle();

    expect(find.text('Xóa Strategy Canvas'), findsOneWidget);
    expect(find.text('Hành động này sẽ xóa vĩnh viễn Canvas'), findsOneWidget);
    expect(find.text('Bạn có chắc chắn muốn xóa không?'), findsOneWidget);
    expect(find.text('Xác nhận Xóa'), findsOneWidget);
  });
}
