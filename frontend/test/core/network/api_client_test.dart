// Task 2 — `ApiClient.resolveRequestTarget` là resolver transport thuần (không
// gửi HTTP) dùng chung cho `get/post/...` VÀ cho `MvpRequestClient`. Test này
// khoá lại đúng invariant: uri/blockedResponse loại trừ lẫn nhau, relay
// routing khi REMOTE_ACCESS, chặn (không tạo Uri) khi OFFLINE, và origin
// đúng cho agent/platform/local-worker.
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '123',
    });
    ApiClient.setBaseUrl('http://company.local');
    ApiClient.setPlatformBaseUrl('http://platform.local');
    ApiClient.setAgentOsBaseUrl('http://agent.local');
    ApiClient.setDesktopWorkerBaseUrl('http://worker.local');
    ApiClient.setRelayBaseUrl('http://gateway.local');
    ApiClient.clearRuntimeContext();
  });

  tearDown(() {
    ApiClient.clearRuntimeContext();
  });

  group('ApiClient.resolveRequestTarget', () {
    test('business endpoint LOCAL_ONLY ⇒ uri thẳng company origin, không blocked', () {
      final target = ApiClient.resolveRequestTarget('/operations/tasks');
      expect(target.blockedResponse, isNull);
      expect(target.uri, isNotNull);
      expect(target.uri.toString(), 'http://company.local/operations/tasks');
    });

    test('business endpoint REMOTE_ACCESS ⇒ uri đi qua relay prefix', () {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      final target = ApiClient.resolveRequestTarget('/operations/tasks');
      expect(target.blockedResponse, isNull);
      expect(target.uri.toString(), 'http://gateway.local/relay/operations/tasks');
    });

    test('business endpoint REMOTE_ACCESS + OFFLINE ⇒ blockedResponse 503, uri null', () {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      final target = ApiClient.resolveRequestTarget('/operations/tasks');
      expect(target.uri, isNull);
      expect(target.blockedResponse, isNotNull);
      expect(target.blockedResponse!.statusCode, 503);
    });

    test('uri và blockedResponse loại trừ lẫn nhau ở mọi nhánh', () {
      for (final scenario in [
        () {
          ApiClient.clearRuntimeContext();
        },
        () => ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE'),
        () => ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE'),
      ]) {
        scenario();
        final target = ApiClient.resolveRequestTarget('/operations/tasks');
        expect(target.uri == null, target.blockedResponse != null);
      }
    });

    test('/platform không đổi target và không bị offline guard', () {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      final target = ApiClient.resolveRequestTarget('/platform/workspaces/1/entitlement');
      expect(target.blockedResponse, isNull);
      expect(target.uri.toString(), 'http://platform.local/platform/workspaces/1/entitlement');
    });

    test('/agent không đổi target và không bị offline guard', () {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      final target = ApiClient.resolveRequestTarget('/agent/workforce/runs');
      expect(target.blockedResponse, isNull);
      expect(target.uri.toString(), 'http://agent.local/agent/workforce/runs');
    });

    test('/local-worker luôn đi origin desktop worker, không bị offline guard', () {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      final target = ApiClient.resolveRequestTarget('/local-worker/status');
      expect(target.blockedResponse, isNull);
      expect(target.uri.toString(), 'http://worker.local/status');
    });
  });
}
