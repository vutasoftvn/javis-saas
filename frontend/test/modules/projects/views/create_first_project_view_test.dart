import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/projects/views/create_first_project_view.dart';

void main() {
  setUp(() {
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('renders CreateFirstProjectView with centered card and elements', (tester) async {
    await tester.pumpWidget(
      const GetMaterialApp(
        home: CreateFirstProjectView(),
      ),
    );
    await tester.pumpAndSettle();

    // Check title and inputs rendered
    expect(find.text('Tạo project đầu tiên'), findsOneWidget);
    expect(find.byType(TextField), findsNWidgets(2));
    expect(find.byType(ElevatedButton), findsOneWidget);
    expect(find.text('Tạo project'), findsOneWidget);
  });
}
