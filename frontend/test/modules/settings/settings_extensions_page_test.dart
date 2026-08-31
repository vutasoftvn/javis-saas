import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/settings/views/settings_extensions_page.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  testWidgets('extensions page makes no legacy network request and explains unavailability', (tester) async {
    ApiClient.client = MockClient((request) async => fail('Extensions page must not call ${request.url}'));

    await tester.pumpWidget(const MaterialApp(home: SettingsExtensionsPage()));
    await tester.pumpAndSettle();

    expect(find.textContaining('chưa khả dụng'), findsOneWidget);
  });
}
