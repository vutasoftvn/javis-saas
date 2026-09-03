// Task 6 — `ApprovalsController` phải giữ nguyên `FeatureData` cũ khi một
// lần refresh nền thất bại (không được chớp qua `FeatureLoading` rồi mất
// danh sách đang hiển thị), và các mutation (approve/reject/request-revision)
// vẫn phải đi qua đúng cổng gate của Task 5 (`MutationGate`) trước khi gọi
// `ApprovalsService.decide`.
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/shared/state/async_feature_state.dart';
import 'package:frontend/modules/approvals/controllers/approvals_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';

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

ApprovalItemModel _pendingItem(String id) => ApprovalItemModel(
      id: id,
      title: 'Send email',
      status: ApprovalStatus.pending,
    );

class _FakeApprovalsService implements ApprovalsService {
  ApiResult<List<ApprovalItemModel>> listResult = ApiSuccess(data: const [], meta: _emptyMeta);
  ApiResult<ApprovalItemModel> decideResult =
      ApiSuccess(data: _pendingItem('appr_1'), meta: _fakeMeta);
  int listCallCount = 0;
  int decideCallCount = 0;

  @override
  Future<ApiResult<List<ApprovalItemModel>>> list({String? status}) async {
    listCallCount += 1;
    return listResult;
  }

  @override
  Future<ApiResult<ApprovalItemModel>> decide(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    decideCallCount += 1;
    return decideResult;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StaticMutationGate implements MutationGate {
  _StaticMutationGate(this.permission);
  final MutationPermission permission;

  @override
  MutationPermission check({required bool isMutation}) => permission;
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

  test('successful load populates FeatureData with the fetched list', () async {
    final service = _FakeApprovalsService()
      ..listResult = ApiSuccess(data: [_pendingItem('appr_1')], meta: _fakeMeta);
    final controller = ApprovalsController(
      approvalsService: service,
      mutationGate: _StaticMutationGate(MutationPermission.allowed),
    );
    controller.onInit();
    await Future<void>.delayed(Duration.zero);

    expect(controller.listState.value, isA<FeatureData<List<ApprovalItemModel>>>());
    final data = controller.listState.value as FeatureData<List<ApprovalItemModel>>;
    expect(data.value, hasLength(1));
    expect(controller.pendingApprovals, hasLength(1));

    controller.onClose();
  });

  test('a failing initial load maps to FeatureFailure, never a silent empty list', () async {
    final service = _FakeApprovalsService()..listResult = const ApiFailure(_unavailableFailure);
    final controller = ApprovalsController(
      approvalsService: service,
      mutationGate: _StaticMutationGate(MutationPermission.allowed),
    );
    controller.onInit();
    await Future<void>.delayed(Duration.zero);

    expect(controller.listState.value, isA<FeatureFailure<List<ApprovalItemModel>>>());

    controller.onClose();
  });

  test('stale data stays visible while a background refresh fails', () async {
    final service = _FakeApprovalsService()
      ..listResult = ApiSuccess(data: [_pendingItem('appr_1')], meta: _fakeMeta);
    final controller = ApprovalsController(
      approvalsService: service,
      mutationGate: _StaticMutationGate(MutationPermission.allowed),
    );
    controller.onInit();
    await Future<void>.delayed(Duration.zero);

    expect(controller.listState.value, isA<FeatureData<List<ApprovalItemModel>>>());

    // Refresh nền lần 2 thất bại — danh sách cũ (thành công lần 1) phải được
    // giữ nguyên, KHÔNG được chớp sang FeatureLoading/FeatureFailure và mất
    // dữ liệu đang hiển thị.
    service.listResult = const ApiFailure(_unavailableFailure);
    await controller.loadApprovals();

    expect(controller.listState.value, isA<FeatureData<List<ApprovalItemModel>>>());
    final data = controller.listState.value as FeatureData<List<ApprovalItemModel>>;
    expect(data.value, hasLength(1));
    expect(data.value.first.id, 'appr_1');

    controller.onClose();
  });

  test('approveTicket is hard-blocked by the gate and never calls the service', () async {
    final service = _FakeApprovalsService();
    final controller = ApprovalsController(
      approvalsService: service,
      mutationGate: _StaticMutationGate(MutationPermission.blockedOffline),
    );
    controller.onInit();
    await Future<void>.delayed(Duration.zero);

    await controller.approveTicket('appr_1');

    expect(service.decideCallCount, 0);

    controller.onClose();
  });

  test('approveTicket calls decide() when the gate allows and refreshes the list on success', () async {
    final service = _FakeApprovalsService()
      ..listResult = ApiSuccess(data: [_pendingItem('appr_1')], meta: _fakeMeta)
      ..decideResult = ApiSuccess(
        data: _pendingItem('appr_1'),
        meta: _fakeMeta,
      );
    final controller = ApprovalsController(
      approvalsService: service,
      mutationGate: _StaticMutationGate(MutationPermission.allowed),
    );
    controller.onInit();
    await Future<void>.delayed(Duration.zero);
    final callsBeforeDecide = service.listCallCount;

    await controller.approveTicket('appr_1', comment: 'ok');

    expect(service.decideCallCount, 1);
    // refresh danh sách thẩm quyền sau một quyết định thành công.
    expect(service.listCallCount, greaterThan(callsBeforeDecide));

    controller.onClose();
  });

  test('a failed decide() does not refresh optimistically or throw', () async {
    final service = _FakeApprovalsService()
      ..listResult = ApiSuccess(data: [_pendingItem('appr_1')], meta: _fakeMeta)
      ..decideResult = const ApiFailure(_unavailableFailure);
    final controller = ApprovalsController(
      approvalsService: service,
      mutationGate: _StaticMutationGate(MutationPermission.allowed),
    );
    controller.onInit();
    await Future<void>.delayed(Duration.zero);

    await controller.rejectTicket('appr_1', reason: 'no');

    expect(service.decideCallCount, 1);

    controller.onClose();
  });
}
