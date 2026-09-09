import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/services/workspace_capability_manifest_controller.dart';
import 'package:frontend/core/services/workspace_capability_manifest_model.dart';
import 'package:frontend/core/services/workspace_capability_manifest_service.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_trial_board_models.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_trial_board_view.dart';

class _FakeApi implements WorkspaceCapabilityManifestApi {
  _FakeApi(this.result);
  final ApiResult<WorkspaceCapabilityManifest> result;
  @override
  Future<ApiResult<WorkspaceCapabilityManifest>> fetch() async => result;
}

Map<String, dynamic> _s(String key, String status) => {
      'surfaceKey': key,
      'moduleKey': 'strategy',
      'featureKey': key,
      'surfaceStatus': status,
      'requiredCapabilities': const [],
      'requiredConnectorKeys': const [],
      'entitled': true,
      'reasons': const [],
      'contractEndpoint': null,
      'releaseNote': status == 'PLANNED' ? 'coming later' : null,
      'updatedAt': '2026-09-09T00:00:00.000Z',
    };

FounderTrialBoard _board() => FounderTrialBoard.fromJson({
      'projectId': 'p1',
      'cycle': {'durationWeeks': 8, 'currentWeek': 2, 'reviews': <dynamic>[]},
      'assumptions': [
        {'id': 'a1', 'statement': 'Weekly pain', 'importance': 9, 'uncertainty': 8, 'riskScore': 72, 'status': 'untested', 'rank': 1, 'isFocus': true},
      ],
      'experiments': [
        {'id': 'e1', 'assumptionId': null, 'hypothesis': 'H', 'method': 'm', 'successCriteria': 's', 'status': 'draft', 'linkedToAssumption': false},
      ],
      'evidence': {
        'candidate': <dynamic>[],
        'approved': <dynamic>[],
        'rejected': <dynamic>[],
        'unlinked': [
          {'id': 'ev1', 'claim': 'loose', 'status': 'candidate', 'supportsOrRefutes': 'supports', 'sourceType': 'interview', 'experimentId': null, 'linkedToExperiment': false, 'observedAt': null},
        ],
      },
      'decisions': <dynamic>[],
    });

Future<WorkspaceCapabilityManifestController> _manifest(List<Map<String, dynamic>> surfaces) async {
  final c = WorkspaceCapabilityManifestController(
    service: _FakeApi(ApiSuccess(
      data: WorkspaceCapabilityManifest.fromJson({
        'version': 'v1',
        'workspaceId': 'ws1',
        'surfaces': surfaces,
      }),
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    )),
  );
  await c.reload();
  return c;
}

void main() {
  testWidgets('renders live sections and a PLANNED roadmap card', (t) async {
    final manifest = await _manifest([
      _s('founder_trial.operating_cycle', 'AVAILABLE'),
      _s('founder_trial.assumptions', 'AVAILABLE'),
      _s('founder_trial.experiments', 'AVAILABLE'),
      _s('founder_trial.evidence', 'AVAILABLE'),
      _s('founder_trial.founder_brief', 'AVAILABLE'),
      _s('finance.cash_liquidity', 'CONFIGURATION_REQUIRED'),
      _s('strategy.pestel', 'PLANNED'),
    ]);

    await t.pumpWidget(MaterialApp(
      home: Scaffold(body: FounderTrialBoardView(board: _board(), manifest: manifest)),
    ));

    expect(find.byKey(const Key('founder_trial_board')), findsOneWidget);
    expect(find.textContaining('Chu kỳ 8 tuần'), findsOneWidget);
    expect(find.text('Weekly pain'), findsOneWidget);
    expect(find.textContaining('chưa liên kết'), findsOneWidget);
    // PLANNED section renders a roadmap card, not the (empty) body.
    expect(find.byKey(const Key('surface_state_planned')), findsOneWidget);
    // finance liquidity needs config.
    expect(find.byKey(const Key('surface_state_configuration_required')), findsOneWidget);
  });

  testWidgets('fail-closed manifest hides every section behind UNAVAILABLE', (t) async {
    // No reload() called → no snapshot → every surface UNAVAILABLE.
    final manifest = WorkspaceCapabilityManifestController(
      service: _FakeApi(ApiSuccess(
        data: WorkspaceCapabilityManifest.fromJson(
            {'version': 'v1', 'workspaceId': 'ws1', 'surfaces': <dynamic>[]}),
        meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
      )),
    );

    await t.pumpWidget(MaterialApp(
      home: Scaffold(body: FounderTrialBoardView(board: _board(), manifest: manifest)),
    ));

    expect(find.byKey(const Key('surface_state_unavailable')), findsWidgets);
    expect(find.text('Weekly pain'), findsNothing);
  });
}
