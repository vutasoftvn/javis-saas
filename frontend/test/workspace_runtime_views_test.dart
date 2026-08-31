import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/workspace_runtime/controllers/workspace_runtime_controller.dart';
import 'package:frontend/modules/workspace_runtime/models/mvp_runtime_models.dart';
import 'package:frontend/modules/workspace_runtime/services/workspace_runtime_service.dart';
import 'package:frontend/modules/workspace_runtime/views/needs_you_view.dart';
import 'package:frontend/modules/workspace_runtime/views/blocked_work_view.dart';

class MockWorkspaceRuntimeService extends WorkspaceRuntimeService {
  @override
  Future<ApiResult<List<MvpRuntimeItem>>> getNeedsYouResult() async {
    return ApiSuccess(
      data: const [],
      meta: ApiResponseMeta(
        dataState: ApiDataState.empty,
        observedAt: DateTime.now(),
        sources: const [ApiSourceRef(kind: 'company_db', ref: 'operating.tasks')],
      ),
    );
  }

  @override
  Future<ApiResult<List<MvpRuntimeItem>>> getBlockersResult() async {
    return ApiSuccess(
      data: const [],
      meta: ApiResponseMeta(
        dataState: ApiDataState.empty,
        observedAt: DateTime.now(),
        sources: const [ApiSourceRef(kind: 'company_db', ref: 'operating.task_dependencies')],
      ),
    );
  }

  @override
  Future<ApiResult<List<MvpSourceStatus>>> getRuntimeStatusResult() async {
    return ApiSuccess(
      data: const [],
      meta: ApiResponseMeta(
        dataState: ApiDataState.empty,
        observedAt: DateTime.now(),
        sources: const [],
      ),
    );
  }
}

void main() {
  setUp(() {
    Get.reset();
  });

  testWidgets('NeedsYouView renders empty state honestly when collection is empty', (tester) async {
    final mockService = MockWorkspaceRuntimeService();
    Get.put(WorkspaceRuntimeController(service: mockService));

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(
          body: NeedsYouView(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Cần bạn xử lý (Needs You)'), findsOneWidget);
    expect(find.text('Tuyệt vời! Không có việc gì cần xử lý ngay bây giờ.'), findsOneWidget);
  });

  testWidgets('BlockedWorkView renders empty state honestly when no blockers', (tester) async {
    final mockService = MockWorkspaceRuntimeService();
    Get.put(WorkspaceRuntimeController(service: mockService));

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(
          body: BlockedWorkView(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Công việc tắc nghẽn (Blocked Work)'), findsOneWidget);
    expect(find.text('Không có công việc nào bị nghẽn (No Blockers)'), findsOneWidget);
  });
}
