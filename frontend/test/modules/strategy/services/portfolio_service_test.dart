import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
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

  group('Portfolio Intelligence', () {
    test('detectPortfolioNecessity makes GET request to detect endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/strategy/portfolios/detect');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({'necessary': true, 'reason': 'Handling multiple projects'}),
          200,
        );
      });

      final result = await PortfolioService().detectPortfolioNecessity();

      expect(result['necessary'], true);
    });

    test('getPortfolios returns portfolios list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios');
        return http.Response(
          jsonEncode({
            'portfolios': [
              {'id': 'port-1', 'name': 'MVP Portfolio'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolios();

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'MVP Portfolio');
      expect(result.isUnavailable, isFalse);
    });

    test('getPortfolios returns failure on 500', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await PortfolioService().getPortfolios();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('createPortfolio posts name and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/portfolios');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Growth Portfolio');
        expect(body['description'], 'For growth initiatives');
        return http.Response(
          jsonEncode({'id': 'port-2', 'name': 'Growth Portfolio'}),
          200,
        );
      });

      final portfolio = await PortfolioService().createPortfolio(
        name: 'Growth Portfolio',
        description: 'For growth initiatives',
      );

      expect(portfolio['id'], 'port-2');
    });

    test('getPortfolioProjects filters by portfolio ID', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/projects');
        return http.Response(
          jsonEncode({
            'projects': [
              {'id': 'proj-1', 'title': 'Mobile App'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioProjects('port-1');

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'Mobile App');
    });

    test('addProjectToPortfolio posts with allocation data', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/portfolios/port-1/projects');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 'proj-1');
        expect(body['strategic_priority'], 'core');
        expect(body['capacity_allocation'], 0.5);
        expect(body['founder_attention_hours'], 10.0);
        return http.Response(jsonEncode({'id': 'link-1'}), 200);
      });

      final result = await PortfolioService().addProjectToPortfolio(
        'port-1',
        projectId: 'proj-1',
        strategicPriority: 'core',
        capacityAllocation: 0.5,
        founderAttentionHours: 10.0,
      );

      expect(result['id'], 'link-1');
    });

    test('removeProjectFromPortfolio calls DELETE', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/strategy/portfolios/port-1/projects/proj-1');
        return http.Response(jsonEncode({'id': 'link-1'}), 200);
      });

      final result = await PortfolioService().removeProjectFromPortfolio('port-1', 'proj-1');

      expect(result['id'], 'link-1');
    });

    test('getPortfolioImpactMatrix fetches impact data', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/impact-matrix');
        return http.Response(
          jsonEncode({'matrix': [[1, 2], [3, 4]]}),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioImpactMatrix('port-1');

      expect(result['matrix'], [[1, 2], [3, 4]]);
    });
  });

  group('SWOT Management', () {
    test('getPortfolioSwot returns swot items list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/swot');
        return http.Response(
          jsonEncode({
            'swot_items': [
              {'id': 'swot-1', 'category': 'strengths', 'statement': 'Strong team'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioSwot('port-1');

      expect(result.items, hasLength(1));
      expect(result.items.first['statement'], 'Strong team');
    });

    test('addPortfolioSwotItem posts with required fields and defaults', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body);
        expect(body['category'], 'strengths');
        expect(body['statement'], 'Good market position');
        expect(body['impact'], 'medium');
        expect(body['likelihood'], 'medium');
        expect(body['confidence'], 'medium');
        expect(body['evidence_status'], 'hypothesis');
        return http.Response(jsonEncode({'id': 'swot-2'}), 200);
      });

      final result = await PortfolioService().addPortfolioSwotItem(
        'port-1',
        category: 'strengths',
        statement: 'Good market position',
      );

      expect(result['id'], 'swot-2');
    });

    test('addPortfolioSwotItem allows custom impact and likelihood', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['impact'], 'high');
        expect(body['likelihood'], 'low');
        expect(body['confidence'], 'high');
        return http.Response(jsonEncode({'id': 'swot-3'}), 200);
      });

      await PortfolioService().addPortfolioSwotItem(
        'port-1',
        category: 'threats',
        statement: 'Market saturation',
        impact: 'high',
        likelihood: 'low',
        confidence: 'high',
      );
    });
  });

  group('TOWS Options', () {
    test('getPortfolioTows returns tows options list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/tows');
        return http.Response(
          jsonEncode({
            'tows_options': [
              {'id': 'tows-1', 'quadrant': 'SO', 'title': 'Grow rapidly'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioTows('port-1');

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'Grow rapidly');
    });

    test('addPortfolioTowsOption posts with quadrant and title', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body);
        expect(body['quadrant'], 'ST');
        expect(body['title'], 'Strengthen positioning');
        expect(body['status'], 'draft');
        return http.Response(jsonEncode({'id': 'tows-2'}), 200);
      });

      final result = await PortfolioService().addPortfolioTowsOption(
        'port-1',
        quadrant: 'ST',
        title: 'Strengthen positioning',
      );

      expect(result['id'], 'tows-2');
    });
  });

  group('Synergies', () {
    test('getPortfolioSynergies returns synergies list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/synergies');
        return http.Response(
          jsonEncode({
            'synergies': [
              {'id': 'syn-1', 'type': 'SHARED_CAPABILITY'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioSynergies('port-1');

      expect(result.items, hasLength(1));
    });

    test('addPortfolioSynergy posts source and target projects', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body);
        expect(body['source_project_id'], 'proj-1');
        expect(body['target_project_id'], 'proj-2');
        expect(body['synergy_type'], 'SHARED_CAPABILITY');
        expect(body['description'], 'Shared tech stack');
        expect(body['status'], 'identified');
        return http.Response(jsonEncode({'id': 'syn-2'}), 200);
      });

      final result = await PortfolioService().addPortfolioSynergy(
        'port-1',
        sourceProjectId: 'proj-1',
        targetProjectId: 'proj-2',
        description: 'Shared tech stack',
      );

      expect(result['id'], 'syn-2');
    });

    test('addPortfolioSynergy includes estimatedValue when provided', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['estimated_value'], 50000.0);
        return http.Response(jsonEncode({'id': 'syn-3'}), 200);
      });

      await PortfolioService().addPortfolioSynergy(
        'port-1',
        sourceProjectId: 'proj-1',
        targetProjectId: 'proj-2',
        description: 'Cost reduction',
        estimatedValue: 50000.0,
      );
    });

    test('deletePortfolioSynergy calls DELETE', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/strategy/portfolios/port-1/synergies/syn-1');
        return http.Response(jsonEncode({'id': 'syn-1'}), 200);
      });

      await PortfolioService().deletePortfolioSynergy('port-1', 'syn-1');
    });
  });

  group('Dependencies', () {
    test('getPortfolioDependencies returns dependencies list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/dependencies');
        return http.Response(
          jsonEncode({
            'dependencies': [
              {'id': 'dep-1', 'type': 'BLOCKS'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioDependencies('port-1');

      expect(result.items, hasLength(1));
    });

    test('addPortfolioDependency posts predecessor and successor', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body);
        expect(body['predecessor_project_id'], 'proj-1');
        expect(body['successor_project_id'], 'proj-2');
        expect(body['dependency_type'], 'BLOCKS');
        return http.Response(jsonEncode({'id': 'dep-2'}), 200);
      });

      final result = await PortfolioService().addPortfolioDependency(
        'port-1',
        predecessorProjectId: 'proj-1',
        successorProjectId: 'proj-2',
      );

      expect(result['id'], 'dep-2');
    });

    test('deletePortfolioDependency calls DELETE', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/strategy/portfolios/port-1/dependencies/dep-1');
        return http.Response(jsonEncode({}), 200);
      });

      await PortfolioService().deletePortfolioDependency('port-1', 'dep-1');
    });
  });

  group('Portfolio Options', () {
    test('getPortfolioOptions returns options list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/options');
        return http.Response(
          jsonEncode({
            'options': [
              {'id': 'opt-1', 'title': 'Option A'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioOptions('port-1');

      expect(result.items, hasLength(1));
    });

    test('createPortfolioOption posts with score defaults', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Growth Option');
        expect(body['strategic_fit_score'], 0.8);
        expect(body['feasibility_score'], 0.7);
        expect(body['risk_level'], 'MEDIUM');
        expect(body['status'], 'draft');
        return http.Response(jsonEncode({'id': 'opt-2'}), 200);
      });

      final result = await PortfolioService().createPortfolioOption(
        'port-1',
        title: 'Growth Option',
      );

      expect(result['id'], 'opt-2');
    });

    test('createPortfolioOption allows custom scores', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['strategic_fit_score'], 0.9);
        expect(body['feasibility_score'], 0.6);
        return http.Response(jsonEncode({'id': 'opt-3'}), 200);
      });

      await PortfolioService().createPortfolioOption(
        'port-1',
        title: 'Premium Option',
        strategicFitScore: 0.9,
        feasibilityScore: 0.6,
      );
    });

    test('updatePortfolioOption puts updated fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/strategy/portfolios/port-1/options/opt-1');
        final body = jsonDecode(request.body);
        expect(body['status'], 'approved');
        return http.Response(jsonEncode({'id': 'opt-1', 'status': 'approved'}), 200);
      });

      final result = await PortfolioService().updatePortfolioOption(
        'port-1',
        'opt-1',
        status: 'approved',
      );

      expect(result['status'], 'approved');
    });
  });

  group('Portfolio Cycles', () {
    test('getPortfolioCycles returns cycles list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolios/port-1/cycles');
        return http.Response(
          jsonEncode({
            'cycles': [
              {'id': 'cycle-1', 'title': 'Q1'},
            ],
          }),
          200,
        );
      });

      final result = await PortfolioService().getPortfolioCycles('port-1');

      expect(result.items, hasLength(1));
    });

    test('createPortfolioCycle posts title and dates', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/portfolios/port-1/cycles');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Q1 2026');
        expect(body['start_date'], '2026-01-01');
        expect(body['end_date'], '2026-03-31');
        return http.Response(jsonEncode({'id': 'cycle-2'}), 200);
      });

      final result = await PortfolioService().createPortfolioCycle(
        'port-1',
        title: 'Q1 2026',
        startDate: '2026-01-01',
        endDate: '2026-03-31',
      );

      expect(result['id'], 'cycle-2');
    });

    test('activatePortfolioCycle posts to activate endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/portfolio-cycles/cycle-1/activate');
        return http.Response(jsonEncode({'id': 'cycle-1', 'status': 'active'}), 200);
      });

      final result = await PortfolioService().activatePortfolioCycle('cycle-1');

      expect(result['status'], 'active');
    });

    test('getCycleAllocations fetches allocation data', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/portfolio-cycles/cycle-1/allocations');
        return http.Response(
          jsonEncode({'allocations': []}),
          200,
        );
      });

      final result = await PortfolioService().getCycleAllocations('cycle-1');

      expect(result['allocations'], isEmpty);
    });
  });

  group('Capacity Allocation', () {
    test('setCapacityAllocation posts project and percentage', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/portfolio-cycles/cycle-1/allocations/capacity');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 'proj-1');
        expect(body['allocated_percentage'], 0.5);
        return http.Response(jsonEncode({'id': 'alloc-1'}), 200);
      });

      final result = await PortfolioService().setCapacityAllocation(
        'cycle-1',
        projectId: 'proj-1',
        allocatedPercentage: 0.5,
      );

      expect(result['id'], 'alloc-1');
    });

    test('setFounderAttentionAllocation posts hours per week', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/portfolio-cycles/cycle-1/allocations/founder-attention');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 'proj-1');
        expect(body['allocated_hours_per_week'], 10.0);
        return http.Response(jsonEncode({'id': 'alloc-2'}), 200);
      });

      final result = await PortfolioService().setFounderAttentionAllocation(
        'cycle-1',
        projectId: 'proj-1',
        allocatedHoursPerWeek: 10.0,
      );

      expect(result['id'], 'alloc-2');
    });
  });

  group('Error Handling', () {
    test('methods throw StrategyApiException on error response', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Portfolio not found'}),
          404,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => PortfolioService().detectPortfolioNecessity(),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 404)
              .having((e) => e.message, 'message', 'Portfolio not found'),
        ),
      );
    });

    test('lists return failure on 500 error', () async {
      ApiClient.client = MockClient((request) async => http.Response('error', 500));

      final result = await PortfolioService().getPortfolios();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('methods throw exception when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});

      expect(
        () => PortfolioService().detectPortfolioNecessity(),
        throwsA(isA<StrategyApiException>()),
      );
    });
  });
}
