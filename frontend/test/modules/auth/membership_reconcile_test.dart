import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/services/fakes/fake_secret_store.dart';

// Plan 2026-09-25 core-auth Task 4 — đối soát membership có giới hạn: chỉ khi
// /identity/me báo quá tuổi quan sát, đồng bộ lại bằng token Core của người dùng,
// có giãn cách, và lỗi không bao giờ làm mất phiên hay bị coi là thành công.

http.Response _json(Object body, int status) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;
  late List<String> calls;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
    AuthService.resetMembershipReconcileForTest();
    originalClient = ApiClient.client;
    calls = [];
  });

  tearDown(() {
    ApiClient.client = originalClient;
    SecureStorageService.resetForTest();
    AuthService.setCachedToken(null);
    AuthService.resetMembershipReconcileForTest();
  });

  test('does nothing while the membership observation is fresh', () async {
    ApiClient.client = MockClient((request) async {
      calls.add(request.url.path);
      return _json({}, 200);
    });
    final outcome = await AuthService().reconcileMembershipIfStale({'membershipObservationStale': false});
    expect(outcome, MembershipReconcileOutcome.notNeeded);
    expect(calls, isEmpty);
  });

  test('re-syncs with the Core token when the observation is stale', () async {
    await SecureStorageService.write('platform_access_token', 'core-token');
    ApiClient.client = MockClient((request) async {
      calls.add(request.url.path);
      expect(request.url.path, '/identity/sync-from-platform');
      expect(jsonDecode(request.body), {'platform_access_token': 'core-token'});
      return _json({
        'local_session_token': 'fresh-local-session',
        'token_type': 'bearer',
        'workspaces': [
          {'workspaceId': '4242', 'name': 'COSA', 'role': 'founder', 'status': 'active'},
        ],
      }, 200);
    });

    final outcome = await AuthService().reconcileMembershipIfStale({'membershipObservationStale': true});
    expect(outcome, MembershipReconcileOutcome.synced);
    expect(calls, ['/identity/sync-from-platform']);
    expect(await SecureStorageService.read('local_session_token'), 'fresh-local-session');
  });

  test('throttles repeated reconciles triggered by many /identity/me calls', () async {
    await SecureStorageService.write('platform_access_token', 'core-token');
    ApiClient.client = MockClient((request) async {
      calls.add(request.url.path);
      return _json({'local_session_token': 't', 'workspaces': []}, 200);
    });
    final service = AuthService();
    final t0 = DateTime(2026, 9, 26, 10);
    expect(await service.reconcileMembershipIfStale({'membershipObservationStale': true}, now: t0),
        MembershipReconcileOutcome.synced);
    expect(
      await service.reconcileMembershipIfStale(
        {'membershipObservationStale': true},
        now: t0.add(const Duration(minutes: 1)),
      ),
      MembershipReconcileOutcome.throttled,
    );
    expect(
      await service.reconcileMembershipIfStale(
        {'membershipObservationStale': true},
        now: t0.add(const Duration(minutes: 6)),
      ),
      MembershipReconcileOutcome.synced,
    );
    expect(calls.length, 2);
  });

  test('keeps the current session when Core cannot be reached', () async {
    await SecureStorageService.write('platform_access_token', 'core-token');
    await SecureStorageService.write('local_session_token', 'existing-session');
    ApiClient.client = MockClient((request) async => _json({'message': 'control-plane down'}, 503));

    final outcome = await AuthService().reconcileMembershipIfStale({'membershipObservationStale': true});
    expect(outcome, MembershipReconcileOutcome.failed);
    expect(await SecureStorageService.read('local_session_token'), 'existing-session');
  });

  test('reports a missing Core token instead of pretending the membership is confirmed', () async {
    ApiClient.client = MockClient((request) async {
      fail('must not call the API without a Core token');
    });
    final outcome = await AuthService().reconcileMembershipIfStale({'membershipObservationStale': true});
    expect(outcome, MembershipReconcileOutcome.noPlatformToken);
  });
}
