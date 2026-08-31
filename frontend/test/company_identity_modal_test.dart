// frontend/test/company_identity_modal_test.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/widgets/company_identity_modal.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({
    'workspace_id': 'ws_1',
  });

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  Future<void> pumpModal(WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: CompanyIdentityModal(workspaceId: 'ws_1')),
      ),
    );
  }

  testWidgets('Save button is disabled until all three fields are filled', (tester) async {
    await pumpModal(tester);

    final saveBtn = find.widgetWithText(ElevatedButton, 'Lưu');
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('company_identity_vision_field')), 'Vision');
    await tester.enterText(find.byKey(const Key('company_identity_mission_field')), 'Mission');
    await tester.pump();
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('company_identity_values_field')), 'Values');
    await tester.pump();
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNotNull);
  });

  testWidgets('Save button taps and initiates save flow', (tester) async {
    // Mock the HTTP client to capture the save request
    ApiClient.client = MockClient((request) async {
      // Return success response for any PATCH request to company identity
      if (request.method == 'PATCH' && request.url.toString().contains('company-identity')) {
        return http.Response(
          '{"id":"ws_1","vision":"Vision text","mission":"Mission text","coreValues":"Values text"}',
          200,
        );
      }
      return http.Response('not found', 404);
    });

    await pumpModal(tester);
    await tester.enterText(find.byKey(const Key('company_identity_vision_field')), 'Vision text');
    await tester.enterText(find.byKey(const Key('company_identity_mission_field')), 'Mission text');
    await tester.enterText(find.byKey(const Key('company_identity_values_field')), 'Values text');
    await tester.pump();

    // Verify save button is enabled
    final saveBtn = find.widgetWithText(ElevatedButton, 'Lưu');
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNotNull);

    // Tap save button
    await tester.tap(saveBtn);
    // Pump to allow the async operation to start and show loading indicator
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify loading indicator appears (indicating save operation started)
    expect(find.byType(CircularProgressIndicator), findsWidgets);
  });

  testWidgets('modal has no dismiss affordance (blocking)', (tester) async {
    await pumpModal(tester);
    expect(find.byIcon(Icons.close), findsNothing);
    expect(find.byType(BackButton), findsNothing);
  });
}
