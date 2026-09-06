import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/strategy/models/strategy_workflow_models.dart';
import 'package:frontend/modules/strategy/services/strategy_workflow_service.dart';
import 'package:frontend/modules/strategy/services/strategy_lens_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('workspace_id', '123456');
  });

  tearDown(() {
    ApiClient.client = http.Client();
  });

  group('StrategyWorkflowService', () {
    test(
      'getWorkspaceSettings sends GET /operations/strategy/settings with headers',
      () async {
        final requestedPaths = <String>[];
        final headersCaptured = <Map<String, String>>[];

        ApiClient.client = MockClient((request) async {
          requestedPaths.add(request.url.path);
          headersCaptured.add(request.headers);

          return http.Response(
            jsonEncode({
              'workspaceId': '123456',
              'strategyMethod': 'BSC_FILTER',
              'bscMode': 'REQUIRED',
              'enabledBscPerspectives': ['FINANCIAL', 'CUSTOMER'],
              'towsSelectionLimit': 2,
              'weeklyReviewEnabled': true,
              'midCycleReviewPolicy': 'AUTO',
              'endCycleReviewEnabled': true,
              'allowedAgentProfiles': ['strategy', 'operations'],
              'approvalPolicy': 'FOUNDER_ONLY',
              'revision': 3,
              'canEdit': true,
            }),
            200,
          );
        });

        final service = StrategyWorkflowService();
        final settings = await service.getWorkspaceSettings();

        expect(requestedPaths, ['/operations/strategy/settings']);
        expect(headersCaptured.first['X-Workspace-Id'], '123456');
        expect(headersCaptured.first['Authorization'], contains('test-token'));

        expect(settings.workspaceId, '123456');
        expect(settings.strategyMethod, StrategyMethod.bscFilter);
        expect(settings.bscMode, BscMode.required);
        expect(settings.enabledBscPerspectives, [
          BscPerspective.financial,
          BscPerspective.customer,
        ]);
        expect(settings.towsSelectionLimit, 2);
        expect(settings.revision, 3);
      },
    );

    test(
      'updateWorkspaceSettings maps 409 conflict to RevisionConflictException',
      () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({
              'message': 'Strategy settings conflict: expected 1, current is 2',
              'currentRevision': 2,
            }),
            409,
          );
        });

        final service = StrategyWorkflowService();
        expect(
          () => service.updateWorkspaceSettings(
            settings: const WorkspaceStrategySettingsModel(
              workspaceId: '123456',
              strategyMethod: StrategyMethod.classic,
              bscMode: BscMode.off,
              enabledBscPerspectives: [],
              towsSelectionLimit: 1,
              weeklyReviewEnabled: true,
              midCycleReviewPolicy: MidCycleReviewPolicy.auto,
              endCycleReviewEnabled: true,
              allowedAgentProfiles: [],
              approvalPolicy: ApprovalPolicy.founderOnly,
              revision: 1,
            ),
            expectedRevision: 1,
          ),
          throwsA(
            isA<RevisionConflictException>().having(
              (e) => e.message,
              'message',
              contains('conflict'),
            ),
          ),
        );
      },
    );

    test(
      'listStrategicObjectives, PESTEL, SWOT and TOWS request paths',
      () async {
        final paths = <String>[];

        ApiClient.client = MockClient((request) async {
          paths.add(request.url.path);
          final jsonHeaders = {
            'content-type': 'application/json; charset=utf-8',
          };
          if (request.url.path == '/operations/strategy/objectives') {
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'id': 'obj_1',
                    'workspaceId': '123456',
                    'title': 'Mục tiêu tăng trưởng Q4',
                    'status': 'PUBLISHED',
                    'revision': 1,
                  },
                ],
              }),
              200,
              headers: jsonHeaders,
            );
          }
          if (request.url.path ==
              '/operations/strategy/objectives/obj_1/analysis/pestel') {
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'id': 'p_1',
                    'workspaceId': '123456',
                    'strategicObjectiveId': 'obj_1',
                    'dimension': 'ECONOMIC',
                    'statement': 'Lãi suất vay giảm',
                    'impact': 'HIGH',
                    'certainty': 'HIGH',
                    'status': 'ACTIVE',
                    'revision': 1,
                  },
                ],
              }),
              200,
              headers: jsonHeaders,
            );
          }
          if (request.url.path ==
              '/operations/strategy/objectives/obj_1/analysis/swot') {
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'id': 's_1',
                    'workspaceId': '123456',
                    'strategicObjectiveId': 'obj_1',
                    'kind': 'OPPORTUNITY',
                    'statement': 'Chi phí vốn rẻ',
                    'sourceType': 'PESTEL_SIGNAL',
                    'sourceId': 'p_1',
                    'revision': 1,
                  },
                ],
              }),
              200,
              headers: jsonHeaders,
            );
          }
          if (request.url.path ==
              '/operations/strategy/objectives/obj_1/tows-options') {
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'id': 't_1',
                    'workspaceId': '123456',
                    'strategicObjectiveId': 'obj_1',
                    'quadrant': 'SO',
                    'title': 'Vay vốn mở rộng nhà máy',
                    'rationale': 'Ưu tiên nguồn vốn chi phí thấp',
                    'status': 'DRAFT',
                    'priorityScore': 4.5,
                    'scoredByMemberId': 'member-1',
                    'revision': 1,
                  },
                ],
              }),
              200,
              headers: jsonHeaders,
            );
          }
          return http.Response('{}', 200, headers: jsonHeaders);
        });

        final service = StrategyWorkflowService();
        final objs = await service.listStrategicObjectives();
        expect(objs, hasLength(1));
        expect(objs.first.id, 'obj_1');

        final pestels = await service.listPestelSignals('obj_1');
        expect(pestels, hasLength(1));
        expect(pestels.first.dimension, PestelDimension.economic);

        final swots = await service.listSwotItems('obj_1');
        expect(swots, hasLength(1));
        expect(swots.first.itemType, SwotItemType.opportunity);
        expect(swots.first.sourcePestelSignalId, 'p_1');

        final tows = await service.listTowsOptions('obj_1');
        expect(tows, hasLength(1));
        expect(tows.first.optionType, TowsOptionType.so);
        expect(tows.first.rankingScore, 4.5);
        expect(tows.first.description, 'Ưu tiên nguồn vốn chi phí thấp');
        expect(tows.first.evaluatedByMemberId, 'member-1');

        expect(paths, contains('/operations/strategy/objectives'));
        expect(
          paths,
          contains('/operations/strategy/objectives/obj_1/analysis/pestel'),
        );
        expect(
          paths,
          contains('/operations/strategy/objectives/obj_1/analysis/swot'),
        );
        expect(
          paths,
          contains('/operations/strategy/objectives/obj_1/tows-options'),
        );
      },
    );

    test(
      'evaluateTowsOption uses the canonical evaluations route and reloads the option',
      () async {
        final paths = <String>[];

        ApiClient.client = MockClient((request) async {
          paths.add(request.url.path);
          if (request.url.path ==
                  '/operations/strategy/tows-options/t_1/evaluations' &&
              request.method == 'POST') {
            return http.Response(
              jsonEncode({
                'id': 'evaluation_1',
                'towsOptionId': 't_1',
                'impactScore': 5,
                'difficultyScore': 2,
                'priorityScore': 8,
                'rationale': 'Impact cao, khó vừa phải',
                'scoredByMemberId': 'member-1',
              }),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
          if (request.url.path == '/operations/strategy/tows-options/t_1' &&
              request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'id': 't_1',
                'workspaceId': '123456',
                'strategicObjectiveId': 'obj_1',
                'quadrant': 'SO',
                'title': 'Mở rộng kênh',
                'status': 'DRAFT',
                'impactScore': 5,
                'difficultyScore': 2,
                'priorityScore': 8,
                'revision': 2,
              }),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
          return http.Response('not found', 404);
        });

        final option = await StrategyWorkflowService().evaluateTowsOption(
          't_1',
          impactScore: 5,
          difficultyScore: 2,
          rationale: 'Impact cao, khó vừa phải',
        );

        expect(paths, [
          '/operations/strategy/tows-options/t_1/evaluations',
          '/operations/strategy/tows-options/t_1',
        ]);
        expect(option.rankingScore, 8);
        expect(option.impactScore, 5);
        expect(option.difficultyScore, 2);
      },
    );

    test('maps the canonical resource-capability contract', () {
      final resource = ResourceCapabilityAssessmentModel.fromJson({
        'id': 'resource_1',
        'workspaceId': '123456',
        'strategicObjectiveId': 'obj_1',
        'category': 'TECHNOLOGY_OPERATIONAL_ASSET',
        'statement': 'Platform scales predictably',
        'strengthLevel': 'STRONG',
        'status': 'ACTIVE',
        'revision': 2,
      });

      expect(resource.maturityLevel, 'STRONG');
      expect(resource.isStrength, isTrue);
    });

    test(
      'createInitiative persists the owner and linked Key Results',
      () async {
        Map<String, dynamic>? payload;
        ApiClient.client = MockClient((request) async {
          payload = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode({
              'id': 'initiative_1',
              'workspaceId': '123456',
              'title': 'Launch onboarding',
              'status': 'active',
              'approvalStatus': 'DRAFT',
              'ownerMemberId': 'member_1',
              'keyResultIds': ['kr_1', 'kr_2'],
              'revision': 1,
            }),
            200,
          );
        });

        final initiative = await StrategyWorkflowService().createInitiative(
          title: 'Launch onboarding',
          ownerMemberId: 'member_1',
          keyResultIds: const ['kr_1', 'kr_2'],
        );

        expect(payload?['ownerMemberId'], 'member_1');
        expect(payload?['keyResultIds'], ['kr_1', 'kr_2']);
        expect(initiative.ownerMemberId, 'member_1');
        expect(initiative.keyResultIds, ['kr_1', 'kr_2']);
      },
    );

    test('tolerates unknown enum values in deserialization', () {
      final json = {
        'workspaceId': '123456',
        'strategyMethod': 'NEW_FUTURE_METHOD',
        'bscMode': 'UNKNOWN_MODE',
        'enabledBscPerspectives': ['FINANCIAL', 'FUTURE_PERSPECTIVE'],
        'towsSelectionLimit': 1,
        'weeklyReviewEnabled': true,
        'midCycleReviewPolicy': 'EXPANDED_POLICY',
        'endCycleReviewEnabled': true,
        'allowedAgentProfiles': [],
        'approvalPolicy': 'MULTI_STAGE_POLICY',
        'revision': 1,
      };

      final settings = WorkspaceStrategySettingsModel.fromJson(json);
      expect(settings.strategyMethod, StrategyMethod.unknown);
      expect(settings.bscMode, BscMode.unknown);
      expect(settings.midCycleReviewPolicy, MidCycleReviewPolicy.unknown);
      expect(settings.approvalPolicy, ApprovalPolicy.unknown);
      expect(settings.enabledBscPerspectives, [BscPerspective.financial]);
    });

    test(
      'never emits requests to ghost routes starting with /strategy/lenses',
      () async {
        final interceptedPaths = <String>[];

        ApiClient.client = MockClient((request) async {
          interceptedPaths.add(request.url.path);
          if (request.url.path == '/operations/strategy/objectives') {
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'id': 'obj_1',
                    'workspaceId': '123456',
                    'title': 'Legacy objective',
                    'status': 'DRAFT',
                    'revision': 1,
                  },
                ],
              }),
              200,
            );
          }
          if (request.url.path ==
              '/operations/strategy/objectives/obj_1/analysis/pestel') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path ==
              '/operations/strategy/objectives/obj_1/analysis/swot') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path ==
              '/operations/strategy/objectives/obj_1/tows-options') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        // Both StrategyWorkflowService and deprecated StrategyLensService adapter must NOT call /strategy/lenses/*
        final workflowService = StrategyWorkflowService();
        await workflowService.listStrategicObjectives();

        @pragma('vm:entry-point')
        final lensService = StrategyLensService(
          workflowService: workflowService,
        );
        await lensService.getStageLensSummary(1);
        await lensService.getPestelSignals(1);
        await lensService.getSwotItems(1);
        await lensService.getTowsMatrix(1);

        expect(interceptedPaths, isNotEmpty);
        for (final p in interceptedPaths) {
          expect(
            p.startsWith('/strategy/lenses'),
            isFalse,
            reason: 'Path $p must not start with ghost route /strategy/lenses',
          );
        }
      },
    );
  });
}
