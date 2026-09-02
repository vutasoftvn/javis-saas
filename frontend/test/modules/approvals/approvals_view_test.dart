// Task 6 — chứng minh ApprovalsView hiển thị đúng UI "không thể tải, có thể
// thử lại" khi tải danh sách approval thất bại, KHÔNG BAO GIỜ để nó trông
// giống hệt copy ăn mừng "Tuyệt vời! Không có yêu cầu nào đang chờ phê
// duyệt." của trạng thái 200-rỗng thật sự.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/modules/approvals/controllers/approvals_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';
import 'package:frontend/modules/approvals/views/approvals_view.dart';

final _fakeMeta = ApiResponseMeta(
  dataState: ApiDataState.populated,
  observedAt: DateTime.utc(2026, 9, 2),
);

final _emptyMeta = ApiResponseMeta(
  dataState: ApiDataState.empty,
  observedAt: DateTime.utc(2026, 9, 2),
);

const _unavailableFailure = ApiFailureDetail(
  code: ApiFailureCode.unavailable,
  statusCode: 503,
  message: 'Service temporarily unavailable',
);

class _FakeApprovalsService implements ApprovalsService {
  ApiResult<List<ApprovalItemModel>> listResult = ApiSuccess(data: const [], meta: _emptyMeta);

  @override
  Future<ApiResult<List<ApprovalItemModel>>> list({String? status}) async => listResult;

  @override
  Future<ApiResult<ApprovalItemModel>> decide(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async =>
      ApiSuccess(
        data: ApprovalItemModel(id: approvalId, title: 't', status: ApprovalStatus.approved),
        meta: _fakeMeta,
      );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _AlwaysAllowGate implements MutationGate {
  // `ApprovalTicketCard` bọc `mutationPermission()` trong một `Obx` riêng
  // (Task 5) để tự disable control khi runtime đổi — GetX bắt buộc `Obx`
  // phải đọc ít nhất một `Rx` bên trong closure của nó, nếu không sẽ ném
  // "improper use of a GetX" dù logic vẫn đúng. Gate thật (`SessionMutationGate`)
  // đọc `SessionController.active` (một Rx); double giả này phải mô phỏng
  // đúng việc đó bằng một `Rx` nội bộ để không phá vỡ hợp đồng của widget
  // không nằm trong phạm vi Task 6.
  final _tick = 0.obs;

  @override
  MutationPermission check({required bool isMutation}) {
    // ignore: unnecessary_statements
    _tick.value;
    return MutationPermission.allowed;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.testMode = true;
    Get.reset();
  });

  tearDown(() {
    Get.reset();
  });

  void setWideSurface(WidgetTester tester) {
    tester.view.physicalSize = const Size(1600, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets(
    'renders retryable unavailable state instead of success empty copy',
    (tester) async {
      final service = _FakeApprovalsService()..listResult = const ApiFailure(_unavailableFailure);
      setWideSurface(tester);
      Get.put<ApprovalsController>(
        ApprovalsController(approvalsService: service, mutationGate: _AlwaysAllowGate()),
      );

      await tester.pumpWidget(const GetMaterialApp(home: ApprovalsView()));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.textContaining('Không thể tải'), findsOneWidget);
      expect(find.text('Thử lại'), findsOneWidget);
      expect(find.textContaining('Tuyệt vời!'), findsNothing);
    },
  );

  testWidgets(
    'still shows the celebratory empty state on a genuine 200-empty response',
    (tester) async {
      final service = _FakeApprovalsService()
        ..listResult = ApiSuccess(data: const [], meta: _emptyMeta);
      setWideSurface(tester);
      Get.put<ApprovalsController>(
        ApprovalsController(approvalsService: service, mutationGate: _AlwaysAllowGate()),
      );

      await tester.pumpWidget(const GetMaterialApp(home: ApprovalsView()));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.textContaining('Tuyệt vời!'), findsOneWidget);
      expect(find.textContaining('Không thể tải'), findsNothing);
    },
  );

  testWidgets(
    'a populated list renders items, not the empty-success copy',
    (tester) async {
      final service = _FakeApprovalsService()
        ..listResult = ApiSuccess(
          data: [
            ApprovalItemModel(
              id: 'appr_1',
              title: 'Send email',
              actionType: 'send_email',
              status: ApprovalStatus.pending,
            ),
          ],
          meta: _fakeMeta,
        );
      setWideSurface(tester);
      Get.put<ApprovalsController>(
        ApprovalsController(approvalsService: service, mutationGate: _AlwaysAllowGate()),
      );

      await tester.pumpWidget(const GetMaterialApp(home: ApprovalsView()));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.textContaining('Tuyệt vời!'), findsNothing);
      expect(find.textContaining('send_email'), findsOneWidget);
    },
  );
}
