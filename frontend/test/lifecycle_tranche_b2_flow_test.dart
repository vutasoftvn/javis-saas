// Task 8 gap-fill (Tranche B2 audit) — cross-plane Flutter flow test.
// Đối chiếu song song với:
//   - tests/apps/cosa/test_lifecycle_tranche_b2_acceptance.py (Python leg)
//   - services/company/operations/strategy/tests/lifecycle-tranche-b2-contract.test.ts (TS leg)
//
// Cùng cấu trúc với lifecycle_tranche_b1_flow_test.dart (sibling tranche):
// vòng gọi service thật (HTTP mock qua ApiClient.client) được kiểm chứng bằng
// `test()` trần (không dùng `testWidgets`) — gọi await một http mock trực tiếp
// bên trong callback `testWidgets` treo vô thời hạn trong `flutter test`
// (AutomatedTestWidgetsFlutterBinding không hoàn tất Future của
// `http.Client.get().timeout(...)` nếu không có `pumpWidget`/`pump` điều
// khiển vòng đời — đã verify bằng probe riêng trước khi viết theo pattern
// này). Phần render UI (`testWidgets`) dùng model đã parse sẵn từ đúng JSON
// backend trả về, không fetch sống bên trong widget.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/pmf_scoreboard_model.dart';
import 'package:frontend/modules/strategy/services/pmf_scoreboard_service.dart';
import 'package:frontend/modules/strategy/widgets/pmf_scoreboard_panel.dart';
import 'package:frontend/modules/strategy/widgets/maturity_track_panel.dart';

Map<String, dynamic> _runJson({required String id, required String result}) => {
      'id': id,
      'workspaceId': '1001',
      'projectId': 'proj-flow-1',
      'contractVersionIds': ['mc-1'],
      'inputSnapshotIds': ['snap-1'],
      'reviewedEvidenceIds': ['ev-1'],
      'policyVersion': 'v1',
      'scoreComponents': [],
      'missingDataFlags': ['MISSING_RETENTION_D60'],
      'reliabilityFlags': ['STALE_SNAPSHOT:snap-old'],
      'calculationHash': 'sha256_flow_hash_1',
      'result': result,
      'humanReviewState': {},
      'calculatedAt': '2026-08-30T12:00:00Z',
    };

Map<String, dynamic> _maturityJson() => {
      'id': 'mat-flow-1',
      'workspaceId': '1001',
      'projectId': 'proj-flow-1',
      'scoreboardRunId': 'run-flow-1',
      'dimensions': {
        'measurement': {'level': 'GOVERNED', 'rationale': 'Contracts validated', 'missingEvidence': []},
        'value': {'level': 'REPEATABLE', 'rationale': 'Approved interviews', 'missingEvidence': []},
        'retention': {
          'level': 'EARLY',
          'rationale': 'Only one cohort observed',
          'missingEvidence': ['Missing day-60 retention snapshot'],
        },
        'commercial': {
          'level': 'NOT_ASSESSED',
          'rationale': 'No pilot outcome recorded yet',
          'missingEvidence': ['Missing LOI'],
        },
        'operational': {'level': 'REPEATABLE', 'rationale': 'Continuous evidence process', 'missingEvidence': []},
      },
      'assessedAt': '2026-08-30T12:00:00Z',
    };

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

  group('COSA Lifecycle Tranche B2 PMF/Maturity Flow Test', () {
    test(
        'service layer: list/get scoreboard run + list maturity assessments never call a '
        'stage-transition or gate-pass endpoint, and return the expected classification', () async {
      final calledPaths = <String>[];

      final mockClient = MockClient((request) async {
        calledPaths.add(request.url.path);

        if (request.url.path == '/operations/strategy/pmf-scoreboards') {
          return http.Response(
            jsonEncode({
              'items': [_runJson(id: 'run-flow-1', result: 'CONCERNING')],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (request.url.path == '/operations/strategy/maturity-assessments') {
          return http.Response(
            jsonEncode({
              'items': [_maturityJson()],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (request.url.path == '/operations/strategy/pmf-scoreboards/calculate') {
          return http.Response(
            jsonEncode(_runJson(id: 'run-flow-2', result: 'MIXED')),
            201,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('not found', 404);
      });

      ApiClient.client = mockClient;
      final service = PmfScoreboardService();

      final runs = await service.listPmfScoreboardRuns(projectId: 'proj-flow-1');
      expect(runs, hasLength(1));
      expect(runs.first.result, PmfScoreboardResult.concerning);

      final maturityList = await service.listMaturityAssessments(projectId: 'proj-flow-1');
      expect(maturityList, hasLength(1));
      expect(maturityList.first.commercial.level, MaturityLevel.notAssessed);

      final recalculated = await service.calculateScoreboard(
        projectId: 'proj-flow-1',
        contractVersionIds: const ['mc-1'],
        inputSnapshotIds: const ['snap-1'],
        reviewedEvidenceIds: const ['ev-1'],
      );
      expect(recalculated?.result, PmfScoreboardResult.mixed);

      expect(calledPaths, isNotEmpty);
      for (final path in calledPaths) {
        expect(path.contains('transition'), isFalse, reason: 'unexpected stage-transition call: $path');
        expect(path.contains('gate'), isFalse, reason: 'unexpected gate-pass call: $path');
        expect(path.contains('/pass'), isFalse, reason: 'unexpected gate-pass call: $path');
      }
    });

    testWidgets(
        'UI layer: PmfScoreboardPanel + MaturityTrackPanel render classification, freshness and '
        'missing-data from the exact model shapes the service above parses, with no gate-pass affordance',
        (tester) async {
      // Model parsed via cùng factory .fromJson mà PmfScoreboardService dùng —
      // đại diện cho dữ liệu đã đi qua service layer, không phải dữ liệu bịa.
      final run = PmfScoreboardRun.fromJson(_runJson(id: 'run-flow-1', result: 'CONCERNING'));
      final maturityDims = _maturityJson()['dimensions'] as Map<String, dynamic>;
      final maturity = MaturityAssessment.fromJson(_maturityJson());

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: Column(
                children: [
                  PmfScoreboardPanel(run: run),
                  MaturityTrackPanel(assessment: maturity),
                ],
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      // Classification rendered.
      expect(find.textContaining('CONCERNING'), findsOneWidget);

      // Freshness / reliability flag rendered (stale snapshot warning).
      expect(find.textContaining('STALE_SNAPSHOT:snap-old'), findsOneWidget);

      // Missing-data flag rendered.
      expect(find.textContaining('MISSING_RETENTION_D60'), findsOneWidget);

      // Maturity dimensions rendered, including NOT_ASSESSED — sanity check
      // against the raw JSON so this stays honest to what the backend sends.
      expect(maturityDims['commercial']!['level'], 'NOT_ASSESSED');
      expect(find.textContaining('NOT ASSESSED'), findsOneWidget);
      expect(find.textContaining('GOVERNED'), findsOneWidget);

      // No stage-transition / gate-pass affordance anywhere in this UI flow:
      // neither panel exposes a button or label referencing gate/transition.
      expect(find.textContaining('Gate'), findsNothing);
      expect(find.textContaining('Chuyển giai đoạn'), findsNothing);
      expect(find.textContaining('Pass Gate'), findsNothing);
    });
  });
}
