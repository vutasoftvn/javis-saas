import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/projects/services/executive_board_stage_suggestion_service.dart';
import 'package:frontend/modules/projects/widgets/executive_board_stage_suggestion_dialog.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async { SharedPreferences.setMockInitialValues({'workspace_id': 'ws'}); await SecureStorageService.write('auth_token', 'token'); });
  test('reads stage suggestion through generated endpoint without any mutation', () async {
    final httpClient = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/projects/proj-1/executive-board/stage-suggestion');
      return http.Response(jsonEncode({'data': {'stage': 'P1', 'workspaceOfficeToEnable': ['cfo'], 'projectAgentsToDeploy': [], 'stageEligibleRoles': ['cfo']}, 'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []}}), 200, headers: {'content-type': 'application/json'});
    });
    final result = await ExecutiveBoardStageSuggestionService(client: MvpRequestClient(httpClient: httpClient)).getSuggestion('proj-1');
    expect(result, isA<ApiSuccess<ExecutiveBoardStageSuggestion>>());
    expect((result as ApiSuccess).data.workspaceOfficeToEnable, ['cfo']);
  });
  test('rejects a malformed suggestion instead of converting it to empty guidance', () async {
    final httpClient = MockClient((request) async => http.Response(jsonEncode({
      'data': {},
      'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
    }), 200, headers: {'content-type': 'application/json'}));
    final result = await ExecutiveBoardStageSuggestionService(
      client: MvpRequestClient(httpClient: httpClient),
    ).getSuggestion('proj-1');
    expect(result.isFailure, isTrue);
    expect(result.failureOrNull?.code, ApiFailureCode.malformedResponse);
  });
  testWidgets('reports suggestion failure without blocking the completed lifecycle transition', (tester) async {
    final httpClient = MockClient((request) async => http.Response('unavailable', 503));
    final service = ExecutiveBoardStageSuggestionService(
      client: MvpRequestClient(httpClient: httpClient),
    );
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Builder(
      builder: (context) => ElevatedButton(
        onPressed: () => showExecutiveBoardStageSuggestionDialog(
          context,
          projectId: 'proj-1',
          workspaceId: 'ws',
          service: service,
        ),
        child: const Text('done'),
      ),
    ))));
    await tester.tap(find.text('done'));
    await tester.pumpAndSettle();
    expect(find.text('Không thể tải gợi ý Executive Board'), findsOneWidget);
  });
}
