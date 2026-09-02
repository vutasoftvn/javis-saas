// M5 §6 — ApiClient routing theo runtime_mode + offline guard.
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'workspace_id': '123',
    });
    ApiClient.setBaseUrl('http://company.local');
    ApiClient.setPlatformBaseUrl('http://platform.local');
    ApiClient.setRelayBaseUrl('http://gateway.local');
    ApiClient.clearRuntimeContext();
  });

  tearDown(() {
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  test('LOCAL_ONLY / unset ⇒ business request tới company origin trực tiếp', () {
    expect(ApiClient.resolveUri('/operations/tasks').toString(),
        'http://company.local/operations/tasks');
    ApiClient.setRuntimeContext(mode: 'LOCAL_ONLY', presence: 'ONLINE');
    expect(ApiClient.resolveUri('/operations/tasks').toString(),
        'http://company.local/operations/tasks');
  });

  test('REMOTE_ACCESS ⇒ business request đi qua relay /relay prefix', () {
    ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
    expect(ApiClient.resolveUri('/operations/tasks').toString(),
        'http://gateway.local/relay/operations/tasks');
  });

  test('REMOTE_ACCESS KHÔNG đổi target của /platform (control-plane vẫn thẳng)', () {
    ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
    expect(ApiClient.resolveUri('/platform/workspaces/1/entitlement').toString(),
        'http://platform.local/platform/workspaces/1/entitlement');
  });

  Future<http.Response> hit(String endpoint) {
    ApiClient.client = MockClient((_) async => http.Response('{"ok":true}', 200));
    return ApiClient.get(endpoint);
  }

  test('REMOTE_ACCESS + OFFLINE ⇒ business request trả 503 runtime_offline, KHÔNG gửi', () async {
    ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
    var sent = false;
    ApiClient.client = MockClient((_) async {
      sent = true;
      return http.Response('{}', 200);
    });
    final res = await ApiClient.get('/operations/tasks');
    expect(res.statusCode, 503);
    expect(jsonDecode(res.body)['error'], 'runtime_offline');
    expect(sent, isFalse);
  });

  test('REMOTE_ACCESS + OFFLINE ⇒ /platform vẫn đi được (không bị offline guard)', () async {
    ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
    final res = await hit('/platform/workspaces/1/entitlement');
    expect(res.statusCode, 200);
  });

  test('REMOTE_ACCESS + ONLINE ⇒ business request được gửi bình thường', () async {
    ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
    final res = await hit('/operations/tasks');
    expect(res.statusCode, 200);
  });
}
