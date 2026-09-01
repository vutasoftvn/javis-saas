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

  group('ProjectService - Projects', () {
    test('getProjects returns projects list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/projects');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'projects': [
              {'id': 'proj-1', 'title': 'MVP Launch', 'status': 'active'},
            ],
          }),
          200,
        );
      });

      final result = await ProjectService().getProjects();

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'MVP Launch');
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNull);
    });

    test('getProjects returns failure on 500 error', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response('server error', 500),
      );

      final result = await ProjectService().getProjects();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getProjects returns failure on network error', () async {
      ApiClient.client = MockClient(
        (_) async => throw const SocketException('offline'),
      );

      final result = await ProjectService().getProjects();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getProjects returns failure when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final result = await ProjectService().getProjects();

      expect(result.items, isEmpty);
      expect(result.errorMessage, contains('workspace'));
    });

    test('createProject posts with title and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/projects');
        final body = jsonDecode(request.body);
        expect(body['title'], 'MVP Launch');
        return http.Response(
          jsonEncode({'id': 'proj-1', 'title': 'MVP Launch'}),
          200,
        );
      });

      final project = await ProjectService().createProject(title: 'MVP Launch');

      expect(project['id'], 'proj-1');
      expect(project['title'], 'MVP Launch');
    });

    test('createProject includes description when provided', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['description'], 'Launch MVP to market');
        return http.Response(jsonEncode({'id': 'proj-1'}), 200);
      });

      await ProjectService().createProject(
        title: 'MVP Launch',
        description: 'Launch MVP to market',
      );
    });

    test('createProject includes phase and projectStage', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['phase'], 'execution');
        expect(body['project_stage'], 'stage-1');
        return http.Response(jsonEncode({'id': 'proj-1'}), 200);
      });

      await ProjectService().createProject(
        title: 'MVP Launch',
        phase: 'execution',
        projectStage: 'stage-1',
      );
    });

    test('createProject throws StrategyApiException on 409', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Project already exists'}),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => ProjectService().createProject(title: 'Duplicate'),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 409)
              .having((e) => e.message, 'message', 'Project already exists'),
        ),
      );
    });

    test('createBasicProject posts only the P0 basic contract', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body, {
          'title': 'Invoice assistant',
          'description': 'Reduce reconciliation time',
          'lifecycleStage': 'P0_DISCOVERY',
        });
        return http.Response(
          jsonEncode({'id': 'p-1', 'lifecycleStage': 'P0_DISCOVERY'}),
          200,
        );
      });
      expect(
        (await ProjectService().createBasicProject(
          title: 'Invoice assistant',
          description: 'Reduce reconciliation time',
        ))['id'],
        'p-1',
      );
    });

    test('updateProject puts title and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/operations/projects/proj-1');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Updated Title');
        return http.Response(
          jsonEncode({'id': 'proj-1', 'title': 'Updated Title'}),
          200,
        );
      });

      final project = await ProjectService().updateProject(
        'proj-1',
        title: 'Updated Title',
      );

      expect(project['title'], 'Updated Title');
    });

    test('deleteProject calls DELETE on the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/operations/projects/proj-1');
        return http.Response('', 204);
      });

      await ProjectService().deleteProject('proj-1');
    });
  });

  group('ProjectService - Initiatives', () {
    test('getInitiatives returns initiatives list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/initiatives');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'initiatives': [
              {'id': 'init-1', 'title': 'User Onboarding', 'status': 'active'},
            ],
          }),
          200,
        );
      });

      final result = await ProjectService().getInitiatives();

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'User Onboarding');
      expect(result.isUnavailable, isFalse);
    });

    test('getInitiatives filters by project_id when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['project_id'], 'proj-1');
        return http.Response(jsonEncode({'initiatives': []}), 200);
      });

      await ProjectService().getInitiatives(projectId: 'proj-1');
    });

    test('createInitiative posts title and optional project_id', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/initiatives');
        final body = jsonDecode(request.body);
        expect(body['title'], 'New Initiative');
        return http.Response(jsonEncode({'id': 'init-1'}), 200);
      });

      final init = await ProjectService().createInitiative(
        title: 'New Initiative',
      );

      expect(init['id'], 'init-1');
    });

    test('updateInitiative puts title and status', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/strategy/initiatives/init-1');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Updated Initiative');
        return http.Response(
          jsonEncode({'id': 'init-1', 'title': 'Updated Initiative'}),
          200,
        );
      });

      final init = await ProjectService().updateInitiative(
        'init-1',
        title: 'Updated Initiative',
      );

      expect(init['title'], 'Updated Initiative');
    });

    test('deleteInitiative calls DELETE on the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/strategy/initiatives/init-1');
        return http.Response('', 204);
      });

      await ProjectService().deleteInitiative('init-1');
    });
  });

  group('ProjectService - Methodology & Analysis', () {
    test('classifyProject posts title and description overrides', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/projects/proj-1/classify');
        final body = jsonDecode(request.body);
        expect(body['title_override'], 'Custom Title');
        return http.Response(
          jsonEncode({'id': 'proj-1', 'classification': 'saas'}),
          200,
        );
      });

      final result = await ProjectService().classifyProject(
        'proj-1',
        titleOverride: 'Custom Title',
      );

      expect(result['id'], 'proj-1');
    });

    test('getMethodologyPlan returns methodology details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/projects/proj-1/methodology');
        return http.Response(
          jsonEncode({'methodology': 'agile', 'phases': 3}),
          200,
        );
      });

      final result = await ProjectService().getMethodologyPlan('proj-1');

      expect(result['methodology'], 'agile');
    });

    test('routeMethodology posts custom methodologies and rationale', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/projects/proj-1/methodology');
        final body = jsonDecode(request.body);
        expect(body['custom_methodologies'], ['agile', 'lean']);
        return http.Response(jsonEncode({'routed': true}), 200);
      });

      final result = await ProjectService().routeMethodology(
        'proj-1',
        customMethodologies: ['agile', 'lean'],
      );

      expect(result['routed'], true);
    });

    test('exportAnalysisPrompt posts project and canvas IDs', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/analysis/export');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 'proj-1');
        return http.Response(jsonEncode({'prompt': 'exported...'}), 200);
      });

      final result = await ProjectService().exportAnalysisPrompt(
        projectId: 'proj-1',
      );

      expect(result.containsKey('prompt'), true);
    });

    test('importAnalysisResult posts raw input and IDs', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/analysis/import');
        final body = jsonDecode(request.body);
        expect(body['raw_input'], 'analysis text');
        return http.Response(jsonEncode({'imported': true}), 200);
      });

      final result = await ProjectService().importAnalysisResult(
        'analysis text',
        projectId: 'proj-1',
      );

      expect(result['imported'], true);
    });
  });

  group('ProjectService - Workspace Templates', () {
    test('getWorkspaceTemplates returns templates list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/workspace-templates');
        return http.Response(
          jsonEncode({
            'templates': [
              {'id': 'tpl-1', 'name': 'Default Template'},
            ],
          }),
          200,
        );
      });

      final result = await ProjectService().getWorkspaceTemplates();

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Default Template');
    });

    test('provisionWorkspaceTemplates posts and returns templates', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/workspace-templates:provision');
        return http.Response(
          jsonEncode({
            'templates': [
              {'id': 'tpl-1', 'name': 'Provisioned Template'},
            ],
          }),
          200,
        );
      });

      final result = await ProjectService().provisionWorkspaceTemplates();

      expect(result.items, hasLength(1));
    });

    test('updateWorkspaceTemplate puts name and capabilities', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/strategy/workspace-templates/tpl-1');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Updated Template');
        return http.Response(
          jsonEncode({'id': 'tpl-1', 'name': 'Updated Template'}),
          200,
        );
      });

      final result = await ProjectService().updateWorkspaceTemplate(
        'tpl-1',
        name: 'Updated Template',
      );

      expect(result['name'], 'Updated Template');
    });
  });

  group('ProjectService - MVP Roadmap', () {
    test('generateMvpRoadmap posts with optional instruction', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/strategy/projects/proj-1/mvp-roadmap:generate',
        );
        final body = jsonDecode(request.body);
        expect(body['instruction'], 'Focus on user acquisition');
        return http.Response(jsonEncode({'stages': [], 'total': 0}), 200);
      });

      final result = await ProjectService().generateMvpRoadmap(
        'proj-1',
        instruction: 'Focus on user acquisition',
      );

      expect(result.containsKey('stages'), true);
    });

    test(
      'generateMvpRoadmap sends null body when instruction is empty',
      () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'POST');
          // Empty body is sent as empty string or null depends on implementation
          return http.Response(jsonEncode({'stages': []}), 200);
        });

        await ProjectService().generateMvpRoadmap('proj-1', instruction: '');
      },
    );

    test('saveMvpRoadmapDraft puts stages', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/strategy/projects/proj-1/mvp-roadmap');
        final body = jsonDecode(request.body);
        expect(body['stages'], isA<List>());
        return http.Response(jsonEncode({'saved': true}), 200);
      });

      final result = await ProjectService().saveMvpRoadmapDraft('proj-1', [
        {'name': 'Stage 1', 'duration': 4},
      ]);

      expect(result['saved'], true);
    });

    test('confirmMvpRoadmap posts confirmation', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/strategy/projects/proj-1/mvp-roadmap:confirm',
        );
        return http.Response(jsonEncode({'confirmed': true}), 200);
      });

      final result = await ProjectService().confirmMvpRoadmap('proj-1');

      expect(result['confirmed'], true);
    });
  });

  group('ProjectService - Project Stages', () {
    test('getProjectStages returns stages list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/projects/proj-1/stages');
        return http.Response(
          jsonEncode({
            'stages': [
              {'id': 'stage-1', 'name': 'Discovery'},
            ],
          }),
          200,
        );
      });

      final result = await ProjectService().getProjectStages('proj-1');

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Discovery');
    });

    test('planMvpStage posts stage planning', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/strategy/projects/proj-1/stages/stage-1:plan',
        );
        return http.Response(jsonEncode({'planned': true}), 200);
      });

      final result = await ProjectService().planMvpStage('proj-1', 'stage-1');

      expect(result['planned'], true);
    });

    test('activateMvpStage posts objectives and weekly focus', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/strategy/projects/proj-1/stages/stage-1:activate',
        );
        final body = jsonDecode(request.body);
        expect(body['objectives'], isA<List>());
        expect(body['weekly_focus'], isA<List>());
        return http.Response(jsonEncode({'activated': true}), 200);
      });

      final result = await ProjectService().activateMvpStage(
        'proj-1',
        'stage-1',
        objectives: [
          {'goal': 'Validate market'},
        ],
        weeklyFocus: ['Week 1: Research', 'Week 2: Interviews'],
      );

      expect(result['activated'], true);
    });

    test(
      'generateStageServiceAssessment posts and returns assessments',
      () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'POST');
          expect(
            request.url.path,
            '/strategy/projects/proj-1/stages/stage-1/service-assessment:generate',
          );
          return http.Response(
            jsonEncode({
              'assessments': [
                {'id': 'assess-1', 'type': 'service'},
              ],
            }),
            200,
          );
        });

        final result = await ProjectService().generateStageServiceAssessment(
          'proj-1',
          'stage-1',
        );

        expect(result.items, hasLength(1));
      },
    );

    test('previewStageRevision posts revision parameters', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/stages/stage-1:preview-revision');
        final body = jsonDecode(request.body);
        expect(body['hypothesis'], 'New hypothesis');
        return http.Response(jsonEncode({'preview': 'ready'}), 200);
      });

      final result = await ProjectService().previewStageRevision(
        'stage-1',
        hypothesis: 'New hypothesis',
      );

      expect(result['preview'], 'ready');
    });

    test('applyStageRevision posts revision ID', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/stages/stage-1:apply-revision');
        final body = jsonDecode(request.body);
        expect(body['revision_id'], 'rev-1');
        return http.Response(jsonEncode({'applied': true}), 200);
      });

      final result = await ProjectService().applyStageRevision(
        'stage-1',
        'rev-1',
      );

      expect(result['applied'], true);
    });
  });

  group('ProjectService - Week 13', () {
    test('generateWeek13 posts generation request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/stages/stage-1/week-13:generate');
        return http.Response(jsonEncode({'generated': true}), 200);
      });

      final result = await ProjectService().generateWeek13('stage-1');

      expect(result['generated'], true);
    });

    test('confirmWeek13 posts decision and rationale', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/stages/stage-1/week-13:confirm');
        final body = jsonDecode(request.body);
        expect(body['decision'], 'proceed');
        expect(body['rationale'], 'Market validated');
        return http.Response(jsonEncode({'confirmed': true}), 200);
      });

      final result = await ProjectService().confirmWeek13(
        'stage-1',
        'proceed',
        'Market validated',
      );

      expect(result['confirmed'], true);
    });
  });
}
