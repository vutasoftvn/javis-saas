import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/projects/controllers/project_analysis_flow_controller.dart';
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';

Map<String, dynamic> _envelope(Object? data) => {
      'data': data,
      'meta': {
        'dataState': 'populated',
        'observedAt': '2026-09-15T12:00:00Z',
        'sources': [
          {'kind': 'company_db', 'ref': 'operating'},
        ],
      },
    };

void main() {
  late http.Client realClient;

  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  ProjectAnalysisFlowController buildController(
    Future<http.Response> Function(http.Request) handler,
  ) {
    final mockHttp = MockClient(handler);
    // `OkrService.publishObjective` gọi qua `ApiClient.post` (không nhận
    // client tiêm được), khác với `ProjectOperatingLoopService` gọi qua
    // `MvpRequestClient` với `http.Client` riêng — phải override CẢ HAI để
    // mock chặn được toàn bộ chuỗi gọi HTTP trong `submitAndActivate()`,
    // đúng như convention đã dùng ở `test/finance_service_test.dart`.
    ApiClient.client = mockHttp;
    final controller = ProjectAnalysisFlowController(
      projectId: '42',
      projectTitle: 'Test Project',
      initialStage: ProjectStage.p0Discovery,
    );
    // GetxController.onInit() chỉ được framework GetX gọi khi controller đi
    // qua Get.put — ở đây dựng trực tiếp bằng constructor nên phải tự gọi,
    // nếu không `currentStage` (late final) sẽ ném LateInitializationError.
    controller.onInit();
    controller.debugOverrideService(
      ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );
    return controller;
  }

  test('submitAndActivate creates objective before cycle and links sourceObjectiveId', () async {
    final calls = <String>[];
    final controller = buildController((request) async {
      calls.add('${request.method} ${request.url.path}');
      if (request.url.path.endsWith('/operating-loop/objectives')) {
        return http.Response(jsonEncode(_envelope({'id': 'obj_1', 'status': 'draft'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/key-results')) {
        return http.Response(jsonEncode(_envelope({'id': 'kr_1'})), 200);
      }
      if (request.url.path.endsWith('/publish')) {
        return http.Response(jsonEncode({'id': 'obj_1', 'status': 'published'}), 200);
      }
      if (request.url.path.endsWith('/operating-loop/cycles')) {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['sourceObjectiveId'], 'obj_1');
        return http.Response(jsonEncode(_envelope({'id': 'cycle_1'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/weeks')) {
        return http.Response(jsonEncode(_envelope({'id': 'week_1'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/commitments')) {
        return http.Response(jsonEncode(_envelope({'id': 'commit_1'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/tasks')) {
        return http.Response(jsonEncode(_envelope({'id': 'task_1'})), 200);
      }
      return http.Response(jsonEncode(_envelope({})), 200);
    });

    controller.targetCustomerCtrl.text = 'Founder gặp khó khăn pháp lý';
    controller.problemStatementCtrl.text = 'Không nắm vững pháp lý';
    controller.selectedAssumptions.assignAll(['Giả định 1', 'Giả định 2']);
    controller.firstWeekOutcomeCtrl.text = 'Xác thực giải pháp';
    controller.addFirstWeekAction('Hành động 1');

    final ok = await controller.submitAndActivate();

    expect(ok, isTrue);
    expect(controller.errorMessage.value, isNull);
    final objectiveIdx = calls.indexWhere((c) => c.endsWith('/operating-loop/objectives'));
    final cycleIdx = calls.indexWhere((c) => c.endsWith('/operating-loop/cycles'));
    final publishIdx = calls.indexWhere((c) => c.endsWith('/publish'));
    expect(objectiveIdx, greaterThanOrEqualTo(0));
    expect(publishIdx, greaterThan(objectiveIdx));
    expect(cycleIdx, greaterThan(publishIdx));
  });

  test('submitAndActivate surfaces failure and returns false when objective creation fails', () async {
    final controller = buildController((request) async {
      if (request.url.path.endsWith('/operating-loop/objectives')) {
        return http.Response(jsonEncode({'error': 'boom'}), 500);
      }
      return http.Response(jsonEncode(_envelope({'id': 'x'})), 200);
    });

    controller.targetCustomerCtrl.text = 'Founder';
    controller.problemStatementCtrl.text = 'Problem';
    controller.selectedAssumptions.assignAll(['Giả định 1']);
    controller.firstWeekOutcomeCtrl.text = 'Outcome';
    controller.addFirstWeekAction('Action 1');

    final ok = await controller.submitAndActivate();

    expect(ok, isFalse);
    expect(controller.errorMessage.value, isNotNull);
  });
}
