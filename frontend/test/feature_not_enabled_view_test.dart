import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/shared/widgets/feature_not_enabled_view.dart';

void main() {
  testWidgets('explains that a deep-linked feature is disabled', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: FeatureNotEnabledView(featureName: 'Finance'),
    ));

    expect(find.text('Finance chưa được bật'), findsOneWidget);
  });
}
