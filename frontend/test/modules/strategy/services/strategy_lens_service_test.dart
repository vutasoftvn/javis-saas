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

  http.Response jsonResp(dynamic data, [int status = 200]) {
    return http.Response(
      jsonEncode(data),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }

  group('StrategyLensService - Stage Lens Summary', () {
    test('getStageLensSummary returns summary on success', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {
                'id': 'obj-1',
                'workspaceId': 'workspace-1',
                'projectId': '1',
                'title': 'Test Objective',
                'status': 'ACTIVE',
              }
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/analysis/pestel') {
          return jsonResp({'items': []});
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/analysis/swot') {
          return jsonResp({'items': []});
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/tows-options') {
          return jsonResp({'items': []});
        }
        return http.Response('not found', 404);
      });

      final result = await StrategyLensService().getStageLensSummary(1);

      expect(result, isNotNull);
      expect(result!.projectId, 1);
      expect(result.projectStage, 'P1_PROBLEM_VALIDATION');
      expect(result.isBscUnlocked, true);
    });

    test('getStageLensSummary returns fallback summary when objective lookup fails', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getStageLensSummary(1);

      expect(result, isNotNull);
      expect(result!.isBscUnlocked, false);
    });
  });

  group('StrategyLensService - PESTEL Radar', () {
    test('getPestelSignals returns signals list', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/analysis/pestel') {
          return jsonResp({
            'items': [
              {
                'id': '1',
                'workspaceId': '1',
                'dimension': 'ECONOMIC',
                'statement': 'Market growth',
                'impact': 'HIGH',
                'isHypothesisCandidate': true,
                'createdAt': '2026-09-01T00:00:00Z',
              },
            ]
          });
        }
        return http.Response('not found', 404);
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
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/analysis/pestel') {
          expect(request.method, 'POST');
          final body = jsonDecode(request.body);
          expect(body['dimension'], 'ECONOMIC');
          expect(body['statement'], 'Market signal');
          return jsonResp(
            {
              'id': '1',
              'workspaceId': '1',
              'dimension': 'ECONOMIC',
              'statement': 'Market signal',
              'impact': 'MEDIUM',
              'isHypothesisCandidate': false,
            },
            201,
          );
        }
        return http.Response('not found', 404);
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
      final result = await StrategyLensService().convertPestelToHypothesis(1);
      expect(result, isNotNull);
      expect(result!.id, 1);
    });
  });

  group('StrategyLensService - SWOT Analysis', () {
    test('getSwotItems returns items list', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/analysis/swot') {
          return jsonResp({
            'items': [
              {
                'id': '1',
                'workspaceId': '1',
                'kind': 'STRENGTH',
                'statement': 'Strong product-market fit',
                'evidenceRefs': [],
              },
            ]
          });
        }
        return http.Response('not found', 404);
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
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/analysis/swot') {
          expect(request.method, 'POST');
          final body = jsonDecode(request.body);
          expect(body['kind'], 'WEAKNESS');
          expect(body['statement'], 'Limited resources');
          return jsonResp(
            {
              'id': '2',
              'workspaceId': '1',
              'kind': 'WEAKNESS',
              'statement': 'Limited resources',
              'evidenceRefs': [],
            },
            201,
          );
        }
        return http.Response('not found', 404);
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
        statement: 'Test',
      );

      expect(result, isNull);
    });
  });

  group('StrategyLensService - TOWS Matrix', () {
    test('getTowsOptions returns options list', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/tows-options') {
          return jsonResp({
            'items': [
              {
                'id': '1',
                'workspaceId': '1',
                'quadrant': 'SO',
                'title': 'Scale market',
                'status': 'EXPLORING',
                'swotItemIds': [],
              },
            ]
          });
        }
        return http.Response('not found', 404);
      });

      final result = await StrategyLensService().getTowsOptions(1);

      expect(result, hasLength(1));
      expect(result.first.title, 'Scale market');
      expect(result.first.quadrant, TowsType.so);
    });

    test('getTowsOptions returns empty list on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getTowsOptions(1);

      expect(result, isEmpty);
    });

    test('createTowsOption posts option details', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/tows-options') {
          expect(request.method, 'POST');
          final body = jsonDecode(request.body);
          expect(body['quadrant'], 'ST');
          expect(body['title'], 'Defend market');
          return jsonResp(
            {
              'id': '1',
              'workspaceId': '1',
              'quadrant': 'ST',
              'title': 'Defend market',
              'status': 'EXPLORING',
              'swotItemIds': [],
            },
            201,
          );
        }
        return http.Response('not found', 404);
      });

      final result = await StrategyLensService().createTowsOption(
        projectId: 1,
        quadrant: TowsType.st,
        title: 'Defend market',
        strategyDescription: 'Strong defenses',
      );

      expect(result, isNotNull);
      expect(result!.title, 'Defend market');
      expect(result.quadrant, TowsType.st);
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
      final result = await StrategyLensService().convertTowsToTactics(
        optionId: 1,
        tacticTitle: 'Validate MVP',
        weekNumber: 2,
        leadIndicator: 'User feedback',
      );

      expect(result, isNotNull);
      expect(result!.title, 'Validate MVP');
    });
  });

  group('StrategyLensService - Balanced Scorecard', () {
    test('getBscGoals returns goals list', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1') {
          return jsonResp({
            'id': 'obj-1',
            'workspaceId': '1',
            'title': 'Test Obj',
            'status': 'ACTIVE',
            'bscFocusScopes': [
              {
                'id': '1',
                'perspective': 'FINANCIAL',
                'strategicObjectiveId': 'obj-1',
                'focusDescription': 'Increase ARR',
                'weight': 1.0,
              },
            ],
          });
        }
        return http.Response('not found', 404);
      });

      final result = await StrategyLensService().getBscGoals(1);

      expect(result, hasLength(1));
      expect(result.first.objective, 'Increase ARR');
      expect(result.first.perspective, BscPerspective.financial);
    });

    test('getBscGoals returns empty list on error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await StrategyLensService().getBscGoals(1);

      expect(result, isEmpty);
    });

    test('createBscGoal posts goal details', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/objectives') {
          return jsonResp({
            'items': [
              {'id': 'obj-1', 'title': 'Test Obj', 'workspaceId': '1'}
            ]
          });
        }
        if (request.url.path == '/operations/strategy/objectives/obj-1/bsc-focus') {
          expect(request.method, 'PUT');
          final body = jsonDecode(request.body);
          final scopes = body['scopes'] as List<dynamic>;
          expect(scopes.first['perspective'], 'CUSTOMER');
          expect(scopes.first['focusDescription'], 'Improve satisfaction');
          return jsonResp(
            {
              'items': [
                {
                  'id': '2',
                  'perspective': 'CUSTOMER',
                  'strategicObjectiveId': 'obj-1',
                  'focusDescription': 'Improve satisfaction',
                  'weight': 1.0,
                },
              ],
            },
            200,
          );
        }
        return http.Response('not found', 404);
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
