import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/finance/services/finance_service.dart';
import 'package:frontend/core/services/function_status_service.dart';
import 'package:frontend/modules/legal/services/legal_service.dart';
import 'package:frontend/modules/sales/services/sales_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '123'});
  });
  tearDown(() => ApiClient.client = realClient);

  test('finance service loads overview', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/api/v1/finance/overview');
      return http.Response(jsonEncode({'snapshot': {'cash': '100'}}), 200);
    });
    expect((await FinanceService().getOverview())?['cash'], '100');
  });

  test('legal and sales services use tenant-scoped endpoints', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.queryParameters['workspace_id'], '123');
      return http.Response(jsonEncode(request.url.path.endsWith('/leads') ? {'leads': []} : {'function': 'LEGAL'}), 200);
    });
    expect(await LegalService().getStatus(), containsPair('function', 'LEGAL'));
    expect(await SalesService().getLeads(), isEmpty);
  });

  test('function status service returns five function cards', () async {
    ApiClient.client = MockClient((_) async => http.Response(jsonEncode({'functions': List.generate(5, (i) => {'function': '$i'})}), 200));
    expect(await FunctionStatusService().getStatuses(), hasLength(5));
  });
}
