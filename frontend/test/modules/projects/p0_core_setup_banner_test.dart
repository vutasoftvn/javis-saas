import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/hologram_hub/services/executive_advisory_board_service.dart';
import 'package:frontend/modules/projects/widgets/p0_core_setup_banner.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Plan 2026-09-25 Task 7 — tạo Project không báo lỗi giả khi bootstrap P0 Core
// lỗi; màn tiếp theo hiện banner gọi action sửa idempotent của Executive Board.

http.Response _json(Object body, int status) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

ExecutiveAdvisoryBoardService _serviceWith(Future<http.Response> Function(http.Request) handler) =>
    ExecutiveAdvisoryBoardService(client: MvpRequestClient(httpClient: MockClient(handler)));

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '4242'});
    await SecureStorageService.write('auth_token', 'token');
  });

  test('detects an incomplete P0 Core bootstrap from the create project response', () {
    expect(isP0CoreBootstrapIncomplete({'id': '1', 'p0CoreBootstrap': {'status': 'INCOMPLETE', 'errorCode': 'unavailable'}}),
        isTrue);
    expect(isP0CoreBootstrapIncomplete({'id': '1', 'p0CoreBootstrap': {'status': 'COMPLETE'}}), isFalse);
    expect(isP0CoreBootstrapIncomplete({'id': '1'}), isFalse);
  });

  for (final MapEntry(key: label, value: size) in const {
    'phone': Size(390, 844),
    'desktop': Size(1400, 1000),
  }.entries) {
    testWidgets('hides the banner only after the server confirms the repair [$label]', (tester) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = size;
      addTearDown(tester.view.reset);
      var calls = 0;
      final service = _serviceWith((request) async {
        calls += 1;
        expect(request.method, 'POST');
        expect(request.url.path, contains('p1'));
        return calls == 1 ? _json({'code': 'unavailable', 'message': 'P0 Core chưa sẵn sàng'}, 503) : _json({'projectId': 'p1'}, 200);
      });

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: P0CoreSetupBanner(projectId: 'p1', service: service)),
      ));
      expect(find.byKey(const Key('p0-core-setup-banner')), findsOneWidget);

      await tester.tap(find.byKey(const Key('p0-core-setup-action')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('p0-core-setup-banner')), findsOneWidget);
      expect(find.byKey(const Key('p0-core-setup-error')), findsOneWidget);

      await tester.tap(find.byKey(const Key('p0-core-setup-action')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('p0-core-setup-banner')), findsNothing);
      expect(calls, 2);
    });
  }
}
