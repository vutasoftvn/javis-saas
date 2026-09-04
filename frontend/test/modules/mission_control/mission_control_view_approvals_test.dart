// Fix-review (2026-09-02, final review I-2) — `MissionControlController.
// approvalsLoadError` (Task 3) đã được gán đúng khi tải approvals thất bại,
// nhưng trước fix này không widget nào đọc lại field đó: view chỉ nhìn
// `pendingApprovals.isEmpty` và luôn hiện "Không có phê duyệt nào đang chờ."
// + badge "0 PENDING", y hệt trường hợp tải THÀNH CÔNG và thật sự rỗng. Test
// này chứng minh 404/5xx phải hiện một thông báo lỗi khác biệt.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/mission_control/controllers/mission_control_controller.dart';
import 'package:frontend/modules/mission_control/services/mission_control_service.dart';
import 'package:frontend/modules/mission_control/views/mission_control_view.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

final _fakeMeta = ApiResponseMeta(
  dataState: ApiDataState.empty,
  observedAt: DateTime.utc(2026, 1, 1),
);

class _FakeWorkforceMvpService implements WorkforceMvpService {
  ApiResult<List<WorkforceApproval>> approvalsResult =
      ApiSuccess(data: const [], meta: _fakeMeta);

  @override
  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return approvalsResult;
  }

  @override
  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<ApiResult<List<WorkforceRun>>> listRuns({int limit = 50}) async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<List<WorkforceRunEvent>>> listRunEvents(String runId) async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<Map<String, dynamic>>> getOrgChart() async {
    return ApiSuccess(data: const {}, meta: _fakeMeta);
  }

  // Task 13 — bổ sung 5 method mới của `WorkforceMvpService` (workforce
  // dashboard gaps) sau khi interface gốc thêm chúng; fake trước đó
  // `implements` toàn bộ class nên thiếu override làm build lỗi biên dịch,
  // không liên quan gì tới approvals mà test này đang cover.
  @override
  Future<ApiResult<List<WorkforceRosterEntry>>> listRoster() async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<List<WorkforceWorkProduct>>> listWorkProducts() async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<WorkforceExceptionSummary>> listExceptions() async {
    return ApiSuccess(
      data: const WorkforceExceptionSummary(
        total: 0,
        founderGateCount: 0,
        leadNotifyCount: 0,
        hasCritical: false,
        escalations: [],
      ),
      meta: _fakeMeta,
    );
  }

  @override
  Future<ApiResult<WorkforceStageRoster>> getStageRoster(String stageCode) async {
    return ApiSuccess(
      data: const WorkforceStageRoster(
        stage: WorkforceStageRosterStage(stageCode: '', taskCount: 0),
        roster: [],
        summary: WorkforceStageRosterSummary(total: 0, highPriority: 0, medium: 0, locked: 0),
      ),
      meta: _fakeMeta,
    );
  }

  @override
  Future<ApiResult<WorkforceDashboardSummary>> getDashboardSummary() async {
    return ApiSuccess(
      data: const WorkforceDashboardSummary(
        rosterTotal: 0,
        rosterActive: 0,
        openExceptions: 0,
        pendingApprovals: 0,
        workProductsTotal: 0,
      ),
      meta: _fakeMeta,
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.testMode = true;
    Get.reset();
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    Get.reset();
  });

  // View này không có breakpoint responsive nhỏ hơn ~1200px logical width;
  // dùng viewport rộng để test tập trung vào tín hiệu lỗi/rỗng thay vì
  // fail vì RenderFlex overflow không liên quan tới finding đang sửa.
  void setWideSurface(WidgetTester tester) {
    tester.view.physicalSize = const Size(1600, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets(
    'shows an honest load-error message instead of "no approvals pending" '
    'when approvalsLoadError is set',
    (tester) async {
      final workforceMvpService = _FakeWorkforceMvpService()
        ..approvalsResult = const ApiFailure(ApiFailureDetail(
          code: ApiFailureCode.notFound,
          statusCode: 404,
          message: 'Not found',
        ));

      setWideSurface(tester);
      Get.put<MissionControlController>(
        MissionControlController(
          service: MissionControlService(),
          workforceMvpService: workforceMvpService,
        ),
      );

      await tester.pumpWidget(
        const GetMaterialApp(home: MissionControlView()),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('Không có phê duyệt nào đang chờ.'), findsNothing);
      expect(find.textContaining('Không tải được danh sách phê duyệt'), findsOneWidget);
      expect(find.text('LỖI TẢI'), findsOneWidget);
    },
  );

  testWidgets(
    'still shows the honest empty state when approvals genuinely load empty',
    (tester) async {
      final workforceMvpService = _FakeWorkforceMvpService();

      setWideSurface(tester);
      Get.put<MissionControlController>(
        MissionControlController(
          service: MissionControlService(),
          workforceMvpService: workforceMvpService,
        ),
      );

      await tester.pumpWidget(
        const GetMaterialApp(home: MissionControlView()),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('Không có phê duyệt nào đang chờ.'), findsOneWidget);
      expect(find.text('0 PENDING'), findsOneWidget);
    },
  );
}
