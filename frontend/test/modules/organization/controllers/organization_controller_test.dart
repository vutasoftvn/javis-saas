import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/organization/controllers/organization_controller.dart';
import 'package:frontend/modules/organization/models/organization_api_models.dart';
import 'package:frontend/modules/organization/services/organization_service.dart';
import 'package:get/get.dart';

// Spec 2026-09-25 §7 — một lần làm mới lỗi phải giữ dữ liệu cũ và hiện lỗi,
// không đổi thành trạng thái rỗng.

final _meta = ApiResponseMeta(
  dataState: ApiDataState.populated,
  observedAt: DateTime.utc(2026, 9, 25),
);

const _overview = OrganizationOverview(
  organizationId: '1',
  name: 'COSA',
  lifecycleStage: 'W0_IDEA',
  viewerRole: 'founder',
  canManageWorkforce: true,
  humanMemberCount: 1,
  aiMemberCount: 1,
);

const _workforce = OrganizationWorkforce(organizationId: '1', members: [
  OrganizationWorkforceMember(
    id: '10',
    memberType: 'AI_AGENT',
    roleTitle: 'Ops Agent',
    managerMemberId: null,
    status: 'active',
    workspaceAgentId: '77',
  ),
]);

class _FakeOrganizationService extends OrganizationService {
  ApiResult<OrganizationOverview> overviewResult = ApiSuccess(data: _overview, meta: _meta);
  ApiResult<OrganizationWorkforce> workforceResult = ApiSuccess(data: _workforce, meta: _meta);

  @override
  Future<ApiResult<OrganizationOverview>> getOverview() async => overviewResult;

  @override
  Future<ApiResult<OrganizationWorkforce>> listWorkforce() async => workforceResult;
}

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('keeps the last good data and exposes the error when a refresh fails', () async {
    final service = _FakeOrganizationService();
    final controller = OrganizationController(service: service);
    await controller.loadOrganizationData();
    expect(controller.overview.value?.name, 'COSA');
    expect(controller.placeableAgents.single.workspaceAgentId, '77');
    expect(controller.canManageWorkforce, isTrue);

    service.overviewResult = const ApiFailure(
      ApiFailureDetail(code: ApiFailureCode.forbidden, statusCode: 403, message: 'revoked'),
    );
    service.workforceResult = const ApiFailure(
      ApiFailureDetail(code: ApiFailureCode.unavailable, message: 'offline'),
    );
    await controller.loadOrganizationData();

    expect(controller.overview.value?.name, 'COSA');
    expect(controller.workforce.value?.members, hasLength(1));
    expect(controller.overviewError.value?.code, ApiFailureCode.forbidden);
    expect(controller.workforceError.value?.code, ApiFailureCode.unavailable);
  });

  test('maps each failure code to a distinct message', () {
    final messages = {
      for (final code in [
        ApiFailureCode.unauthenticated,
        ApiFailureCode.forbidden,
        ApiFailureCode.notFound,
        ApiFailureCode.invalidRequest,
        ApiFailureCode.unavailable,
      ])
        organizationFailureMessage(ApiFailureDetail(code: code, message: 'm')),
    };
    expect(messages, hasLength(5));
  });
}
