import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/contracts/enums.generated.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';
import 'package:frontend/modules/strategy/services/strategy_service_base.dart';
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

  final sampleSetupJson = {
    'projectId': 'p-1',
    'workspaceId': 'workspace-1',
    'status': 'ACTIVE',
    'targetCustomer': 'B2B Sales Teams',
    'problemStatement': 'Lead qualification is manual and slow',
    'evidenceLevel': 'FIVE_PLUS_INTERVIEWS',
    'recommendedStage': 'P1_PROBLEM_VALIDATION',
    'selectedStage': 'P1_PROBLEM_VALIDATION',
    'stageDurationWeeks': 4,
    'stageTargetDate': '2026-10-01T00:00:00.000Z',
    'weeklyReviewWeekday': 5,
    'weeklyReviewTime': '16:00',
    'firstWeekOutcome': 'Recruit five interviewees',
    'firstWeekActions': [
      {'id': 'a-1', 'title': 'Recruit five interviewees'},
    ],
    'updatedAt': '2026-09-01T00:00:00.000Z',
  };

  final sampleDraft = ProjectOperatingSetupDraft(
    targetCustomer: 'B2B Sales Teams',
    problemStatement: 'Lead qualification is manual and slow',
    evidenceLevel: KickoffEvidenceLevel.fivePlusInterviews,
    selectedStage: ProjectLifecycleStage.p1ProblemValidation,
    stageDurationWeeks: 4,
    weeklyReviewWeekday: 5,
    weeklyReviewTime: '16:00',
    firstWeekOutcome: 'Recruit five interviewees',
    firstWeekActions: const [
      FirstWeekActionDraft(title: 'Recruit five interviewees'),
    ],
  );

  test('get loads operating setup model from API', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/projects/p-1/operating-setup');
      expect(request.headers['X-Workspace-Id'], 'workspace-1');
      return http.Response(jsonEncode(sampleSetupJson), 200);
    });

    final setup = await ProjectOperatingSetupService().get('p-1');
    expect(setup.projectId, 'p-1');
    expect(setup.status, OperatingSetupStatus.active);
    expect(setup.isInitialLoop, isTrue);
    expect(setup.evidenceLevel, KickoffEvidenceLevel.fivePlusInterviews);
    expect(setup.selectedStage, ProjectLifecycleStage.p1ProblemValidation);
    expect(setup.firstWeekActions.length, 1);
    expect(setup.firstWeekActions.first.title, 'Recruit five interviewees');
  });

  test('saveDraft sends draft and returns updated setup', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'PUT');
      expect(request.url.path, '/operations/projects/p-1/operating-setup');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['targetCustomer'], 'B2B Sales Teams');
      expect(body['evidenceLevel'], 'FIVE_PLUS_INTERVIEWS');
      return http.Response(
        jsonEncode({...sampleSetupJson, 'status': 'IN_PROGRESS'}),
        200,
      );
    });

    final setup = await ProjectOperatingSetupService().saveDraft(
      'p-1',
      sampleDraft,
    );
    expect(setup.status, OperatingSetupStatus.inProgress);
    expect(setup.isInitialLoop, isFalse);
  });

  test('activate posts founder actions and no inferred mission', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/operations/projects/p-1/operating-setup/activate',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['firstWeekActions'], [
        {'title': 'Recruit five interviewees'},
      ]);
      expect(body.containsKey('mission'), isFalse);
      expect(body.containsKey('activeMissions'), isFalse);
      return http.Response(jsonEncode({'setup': sampleSetupJson}), 200);
    });

    final setup = await ProjectOperatingSetupService().activate(
      'p-1',
      sampleDraft,
    );
    expect(setup.status, OperatingSetupStatus.active);
    expect(setup.isInitialLoop, isTrue);
  });

  test(
    '422 error throws StrategyApiException rather than empty setup model',
    () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Invalid arguments for activation'}),
          422,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => ProjectOperatingSetupService().activate('p-1', sampleDraft),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 422)
              .having(
                (e) => e.message,
                'message',
                'Invalid arguments for activation',
              ),
        ),
      );
    },
  );
}
