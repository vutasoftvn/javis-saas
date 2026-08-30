// Task 7 gap-fill (Tranche B2 audit) — unit test cho PmfScoreboardService:
// đảm bảo service gọi đúng endpoint GET cho scoreboard run, deserialize đúng
// classification, và không bao giờ gọi endpoint chuyển stage/pass gate.
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/pmf_scoreboard_model.dart';
import 'package:frontend/modules/strategy/services/pmf_scoreboard_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({});
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('local_session_token', 'test-local-token');
    await SecureStorageService.write('workspace_id', '1001');
  });

  tearDown(() {
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  Map<String, dynamic> scoreboardJson({required String result}) => {
        'id': 'run-101',
        'workspaceId': '1001',
        'projectId': 'proj-1',
        'contractVersionIds': ['mc-1'],
        'inputSnapshotIds': ['snap-1'],
        'reviewedEvidenceIds': ['ev-1'],
        'policyVersion': 'v1',
        'scoreComponents': [],
        'missingDataFlags': [],
        'reliabilityFlags': [],
        'calculationHash': 'sha256_deadbeef',
        'result': result,
        'humanReviewState': {},
        'calculatedAt': '2026-08-30T12:00:00Z',
      };

  group('PmfScoreboardService.getPmfScoreboardRun', () {
    test('calls the correct GET endpoint for a scoreboard run', () async {
      String? capturedMethod;
      String? capturedPath;

      final mockClient = MockClient((request) async {
        capturedMethod = request.method;
        capturedPath = request.url.path;
        return http.Response(
          jsonEncode(scoreboardJson(result: 'PROMISING')),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      ApiClient.client = mockClient;
      final service = PmfScoreboardService();

      final run = await service.getPmfScoreboardRun('run-101');

      expect(capturedMethod, 'GET');
      expect(capturedPath, '/operations/strategy/pmf-scoreboards/run-101');
      expect(run, isNotNull);
      expect(run!.id, 'run-101');
      expect(run.calculationHash, 'sha256_deadbeef');
    });

    for (final entry in {
      'INSUFFICIENT_DATA': PmfScoreboardResult.insufficientData,
      'MIXED': PmfScoreboardResult.mixed,
      'PROMISING': PmfScoreboardResult.promising,
      'CONCERNING': PmfScoreboardResult.concerning,
    }.entries) {
      test('correctly deserializes classification ${entry.key}', () async {
        final mockClient = MockClient((request) async {
          return http.Response(
            jsonEncode(scoreboardJson(result: entry.key)),
            200,
            headers: {'content-type': 'application/json'},
          );
        });

        ApiClient.client = mockClient;
        final service = PmfScoreboardService();

        final run = await service.getPmfScoreboardRun('run-101');

        expect(run, isNotNull);
        expect(run!.result, entry.value);
      });
    }

    test('never calls a stage-transition or gate-pass endpoint', () async {
      final calledPaths = <String>[];

      final mockClient = MockClient((request) async {
        calledPaths.add(request.url.path);
        return http.Response(
          jsonEncode(scoreboardJson(result: 'MIXED')),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      ApiClient.client = mockClient;
      final service = PmfScoreboardService();

      await service.getPmfScoreboardRun('run-101');
      await service.listPmfScoreboardRuns(projectId: 'proj-1');
      await service.calculateScoreboard(
        projectId: 'proj-1',
        contractVersionIds: const ['mc-1'],
        inputSnapshotIds: const ['snap-1'],
        reviewedEvidenceIds: const ['ev-1'],
      );

      expect(calledPaths, isNotEmpty);
      for (final path in calledPaths) {
        expect(path.contains('transition'), isFalse, reason: 'unexpected stage-transition call: $path');
        expect(path.contains('gate'), isFalse, reason: 'unexpected gate-pass call: $path');
        expect(path.contains('/pass'), isFalse, reason: 'unexpected gate-pass call: $path');
      }
    });
  });
}
