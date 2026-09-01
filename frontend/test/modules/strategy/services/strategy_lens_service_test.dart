import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/strategy_lens_model.dart';
import 'package:frontend/modules/strategy/services/strategy_lens_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('StrategyLensService - Stage Lens Summary', () {
    test('getStageLensSummary returns summary on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/lenses/summary/1');
        return http.Response(
          jsonEncode({
            'project_id': 1,
            'project_stage': 'P1_PROBLEM_VALIDATION',
            'is_bsc_unlocked': false,
            'pestel_signals': [],
            'swot_items': [],
            'tows_options': [],
            'bsc_goals': [],
          }),
          200,
        );
      });

      final result = await StrategyLensService().getStageLensSummary(1);

      expect(result, isNotNull);
      expect(result!.projectId, 1);
      expect(result.projectStage, 'P1_PROBLEM_VALIDATION');
      expect(result.isBscUnlocked, false);
    });

    test('getStageLensSummary returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getStageLensSummary(1);

      expect(result, isNull);
    });

    test('getStageLensSummary returns null on non-200 status', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('not found', 404);
      });

      final result = await StrategyLensService().getStageLensSummary(1);

      expect(result, isNull);
    });
  });

  group('StrategyLensService - PESTEL Radar', () {
    test('getPestelSignals returns signals list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/lenses/pestel');
        expect(request.url.queryParameters['project_id'], '1');
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'workspace_id': 1,
              'project_id': 1,
              'dimension': 'economic',
              'signal_title': 'Market growth',
              'description': 'Strong market demand',
              'impact_level': 'high',
              'time_horizon': 'short_term',
              'stage_captured': 'P0_DISCOVERY',
              'created_at': '2026-09-01T00:00:00Z',
            },
          ]),
          200,
        );
      });

      final result = await StrategyLensService().getPestelSignals(1);

      expect(result, hasLength(1));
      expect(result.first.signalTitle, 'Market growth');
      expect(result.first.dimension, PestelDimension.economic);
    });

    test('getPestelSignals returns empty list on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getPestelSignals(1);

      expect(result, isEmpty);
    });

    test('createPestelSignal posts signal details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/lenses/pestel');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 1);
        expect(body['dimension'], 'economic');
        expect(body['signal_title'], 'Market signal');
        return http.Response(
          jsonEncode({
            'id': 1,
            'workspace_id': 1,
            'project_id': 1,
            'dimension': 'economic',
            'signal_title': 'Market signal',
            'description': 'Strong market demand',
            'impact_level': 'medium',
            'time_horizon': 'medium_term',
            'stage_captured': 'P0_DISCOVERY',
            'created_at': '2026-09-01T00:00:00Z',
          }),
          201,
        );
      });

      final result = await StrategyLensService().createPestelSignal(
        projectId: 1,
        dimension: PestelDimension.economic,
        signalTitle: 'Market signal',
        description: 'Strong market demand',
      );

      expect(result, isNotNull);
      expect(result!.signalTitle, 'Market signal');
    });

    test('createPestelSignal returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 400));

      final result = await StrategyLensService().createPestelSignal(
        projectId: 1,
        dimension: PestelDimension.political,
        signalTitle: 'Test',
        description: 'Test signal',
      );

      expect(result, isNull);
    });

    test('convertPestelToHypothesis posts conversion', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/lenses/pestel/1/to-hypothesis');
        return http.Response(
          jsonEncode({'id': 1, 'hypothesis_text': 'If market grows...'}),
          201,
        );
      });

      // Note: HypothesisModel needs to be imported from evidence_model.dart
      // For now, we just test that the method returns non-null when successful
      // The actual model parsing would be tested elsewhere
      final result = await StrategyLensService().convertPestelToHypothesis(1);

      expect(result, isNotNull);
    });
  });

  group('StrategyLensService - SWOT Analysis', () {
    test('getSwotItems returns items list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/lenses/swot');
        expect(request.url.queryParameters['project_id'], '1');
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'workspace_id': 1,
              'project_id': 1,
              'category': 'STRENGTH',
              'statement': 'Strong product-market fit',
              'importance': 0.9,
              'evidence_status': 'verified',
              'evidence_refs': [],
              'created_at': '2026-09-01T00:00:00Z',
            },
          ]),
          200,
        );
      });

      final result = await StrategyLensService().getSwotItems(1);

      expect(result, hasLength(1));
      expect(result.first.statement, 'Strong product-market fit');
      expect(result.first.category, SwotType.strength);
    });

    test('getSwotItems returns empty list on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getSwotItems(1);

      expect(result, isEmpty);
    });

    test('createSwotItem posts item details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/lenses/swot');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 1);
        expect(body['category'], 'WEAKNESS');
        expect(body['statement'], 'Limited resources');
        return http.Response(
          jsonEncode({
            'id': 2,
            'workspace_id': 1,
            'project_id': 1,
            'category': 'WEAKNESS',
            'statement': 'Limited resources',
            'importance': 0.7,
            'evidence_status': 'unverified',
            'evidence_refs': [],
            'created_at': '2026-09-01T00:00:00Z',
          }),
          201,
        );
      });

      final result = await StrategyLensService().createSwotItem(
        projectId: 1,
        category: SwotType.weakness,
        statement: 'Limited resources',
      );

      expect(result, isNotNull);
      expect(result!.statement, 'Limited resources');
      expect(result.category, SwotType.weakness);
    });

    test('createSwotItem returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 400));

      final result = await StrategyLensService().createSwotItem(
        projectId: 1,
        category: SwotType.threat,
        statement: 'Market competition',
      );

      expect(result, isNull);
    });
  });

  group('StrategyLensService - TOWS Matrix', () {
    test('getTowsOptions returns options list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/lenses/tows');
        expect(request.url.queryParameters['project_id'], '1');
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'workspace_id': 1,
              'project_id': 1,
              'quadrant': 'SO',
              'title': 'Aggressive growth',
              'expected_impact': 'high',
              'confidence': 'high',
              'status': 'draft',
              'linked_strength_ids': [],
              'linked_weakness_ids': [],
              'linked_opportunity_ids': [],
              'linked_threat_ids': [],
              'tactics_12wy': [],
              'created_at': '2026-09-01T00:00:00Z',
            },
          ]),
          200,
        );
      });

      final result = await StrategyLensService().getTowsOptions(1);

      expect(result, hasLength(1));
      expect(result.first.title, 'Aggressive growth');
      expect(result.first.quadrant, TowsType.so);
    });

    test('getTowsOptions returns empty list on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getTowsOptions(1);

      expect(result, isEmpty);
    });

    test('createTowsOption posts option details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/lenses/tows');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 1);
        expect(body['quadrant'], 'WO');
        expect(body['title'], 'Fix weakness via opportunity');
        return http.Response(
          jsonEncode({
            'id': 2,
            'workspace_id': 1,
            'project_id': 1,
            'quadrant': 'WO',
            'title': 'Fix weakness via opportunity',
            'expected_impact': 'medium',
            'confidence': 'medium',
            'status': 'draft',
            'linked_strength_ids': [],
            'linked_weakness_ids': [],
            'linked_opportunity_ids': [],
            'linked_threat_ids': [],
            'tactics_12wy': [],
            'created_at': '2026-09-01T00:00:00Z',
          }),
          201,
        );
      });

      final result = await StrategyLensService().createTowsOption(
        projectId: 1,
        quadrant: TowsType.wo,
        title: 'Fix weakness via opportunity',
        strategyDescription: 'Leverage market opportunity to strengthen position',
      );

      expect(result, isNotNull);
      expect(result!.title, 'Fix weakness via opportunity');
      expect(result.quadrant, TowsType.wo);
    });

    test('createTowsOption returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 400));

      final result = await StrategyLensService().createTowsOption(
        projectId: 1,
        quadrant: TowsType.st,
        title: 'Test',
        strategyDescription: 'Test description',
      );

      expect(result, isNull);
    });

    test('convertTowsToTactics posts tactic generation', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/lenses/tows/1/generate-tactics');
        final body = jsonDecode(request.body);
        expect(body['tactic_title'], 'Validate MVP');
        expect(body['week_number'], 2);
        return http.Response(
          jsonEncode({
            'id': 1,
            'tactics_12wy': [
              {'title': 'Validate MVP', 'week': 2},
            ],
          }),
          201,
        );
      });

      final result = await StrategyLensService().convertTowsToTactics(
        optionId: 1,
        tacticTitle: 'Validate MVP',
        weekNumber: 2,
        leadIndicator: 'User feedback',
      );

      expect(result, isNotNull);
    });
  });

  group('StrategyLensService - Balanced Scorecard', () {
    test('getBscGoals returns goals list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/lenses/bsc');
        expect(request.url.queryParameters['project_id'], '1');
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'workspace_id': 1,
              'project_id': 1,
              'perspective': 'FINANCIAL',
              'objective': 'Increase revenue',
              'kpi_name': 'MRR',
              'target_value': '10000',
              'current_value': '5000',
              'initiatives': [],
              'status': 'on_track',
              'created_at': '2026-09-01T00:00:00Z',
            },
          ]),
          200,
        );
      });

      final result = await StrategyLensService().getBscGoals(1);

      expect(result, hasLength(1));
      expect(result.first.objective, 'Increase revenue');
      expect(result.first.perspective, BscPerspective.financial);
    });

    test('getBscGoals returns empty list on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getBscGoals(1);

      expect(result, isEmpty);
    });

    test('createBscGoal posts goal details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/lenses/bsc');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 1);
        expect(body['perspective'], 'CUSTOMER');
        expect(body['objective'], 'Improve satisfaction');
        return http.Response(
          jsonEncode({
            'id': 2,
            'workspace_id': 1,
            'project_id': 1,
            'perspective': 'CUSTOMER',
            'objective': 'Improve satisfaction',
            'kpi_name': 'NPS',
            'target_value': '50',
            'current_value': '30',
            'initiatives': [],
            'status': 'at_risk',
            'created_at': '2026-09-01T00:00:00Z',
          }),
          201,
        );
      });

      final result = await StrategyLensService().createBscGoal(
        projectId: 1,
        perspective: BscPerspective.customer,
        objective: 'Improve satisfaction',
        kpiName: 'NPS',
        targetValue: '50',
      );

      expect(result, isNotNull);
      expect(result!.objective, 'Improve satisfaction');
      expect(result.perspective, BscPerspective.customer);
    });

    test('createBscGoal returns null on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 400));

      final result = await StrategyLensService().createBscGoal(
        projectId: 1,
        perspective: BscPerspective.internalOperations,
        objective: 'Test',
        kpiName: 'Test KPI',
        targetValue: '100',
      );

      expect(result, isNull);
    });
  });
}
