import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/settings/controllers/permissions_controller.dart';
import 'package:frontend/modules/settings/models/permission_models.dart';
import 'package:frontend/modules/settings/services/permissions_service.dart';
import 'package:frontend/modules/settings/views/widgets/permissions_panel.dart';

class MockPermissionsService extends PermissionsService {
  bool shouldFailUpdate = false;
  String updateFailureMessage = 'VERSION_CONFLICT: Expected version 1 but current is 2';

  final PermissionsDataModel testData = const PermissionsDataModel(
    catalog: [
      PermissionDefinitionModel(
        permissionKey: 'execution.plan.approve',
        domain: 'operations',
        description: 'Phê duyệt execution plan',
      ),
      PermissionDefinitionModel(
        permissionKey: 'finance.request.create',
        domain: 'finance',
        description: 'Tạo yêu cầu chi tiền',
      ),
    ],
    roles: [
      WorkspaceRoleModel(
        id: 'role-operator-1',
        roleKey: 'operator',
        name: 'Operator',
        isSystem: false,
        permissions: [
          RolePermissionModel(
            permissionKey: 'execution.plan.approve',
            effect: 'DENY',
            conditions: {},
          ),
        ],
      ),
    ],
    assignments: [
      MemberRoleAssignmentModel(
        id: 'assignment-1',
        workforceMemberId: 'member-101',
        roleId: 'role-operator-1',
        roleKey: 'operator',
        roleName: 'Operator',
        validFrom: '2026-09-01T00:00:00Z',
      ),
    ],
    version: 1,
    effectivePermissions: {
      'execution.plan.approve': 'DENY',
      'finance.request.create': 'DENY',
    },
  );

  static final ApiResponseMeta testMeta = ApiResponseMeta(
    dataState: ApiDataState.populated,
    observedAt: DateTime(2026, 9, 5),
    sources: const [],
  );

  @override
  Future<ApiResult<WorkspaceAuthorityOverviewModel>> fetchOverview() async {
    return ApiSuccess(
      data: const WorkspaceAuthorityOverviewModel(
        roles: [],
        assignments: [],
        grants: [],
        bindings: [],
        events: [],
        members: [],
        authorizationEpoch: 1,
        policyVersion: 1,
      ),
      meta: testMeta,
    );
  }

  @override
  Future<ApiResult<PermissionsDataModel>> getPermissions() async {
    return ApiSuccess(data: testData, meta: testMeta);
  }


  @override
  Future<ApiResult<Map<String, dynamic>>> updatePermissions({
    required int expectedVersion,
    required String reason,
    required List<Map<String, dynamic>> mutations,
  }) async {
    if (shouldFailUpdate) {
      return ApiFailure(
        ApiFailureDetail(
          code: ApiFailureCode.conflict,
          message: updateFailureMessage,
        ),
      );
    }
    return ApiSuccess(data: const {'success': true, 'version': 2}, meta: testMeta);
  }

  @override
  Future<ApiResult<SimulatePermissionsResponse>> simulatePermissions({
    required String action,
    String? memberId,
    String? projectId,
    String? legalEntityId,
    Map<String, dynamic>? facts,
  }) async {
    return ApiSuccess(
      data: const SimulatePermissionsResponse(
        decision: {'effect': 'REQUIRE_APPROVAL'},
        impacts: [
          SimulateImpactModel(
            memberId: 'member-101',
            action: 'execution.plan.approve',
            effect: 'REQUIRE_APPROVAL',
            reason: 'Rule requires approval from founder for execution plans',
          ),
        ],
      ),
      meta: testMeta,
    );
  }
}

void main() {
  setUp(() {
    Get.reset();
  });

  testWidgets(
    'editing dropdown does not change effective state before save; save failure displays conflict widget and retains form',
    (tester) async {
      final mockService = MockPermissionsService();
      final controller = Get.put(PermissionsController(service: mockService));

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: PermissionsPanel(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 1. Verify initial state
      expect(find.text('Phân quyền & Governance (Policy v1)'), findsOneWidget);
      expect(find.byKey(const ValueKey('permission-save')), findsOneWidget);
      expect(find.byKey(const ValueKey('permission-simulation')), findsOneWidget);

      // Verify effective state in table is DENY
      expect(controller.permissionsData.value?.effectivePermissions['execution.plan.approve'], 'DENY');

      // 2. Chỉnh dropdown sang ALLOW (local draft edit)
      controller.updateDraftPermission('role-operator-1', 'execution.plan.approve', 'ALLOW');
      await tester.pumpAndSettle();

      // Effective state vẫn giữ nguyên DENY (chưa save!)
      expect(controller.permissionsData.value?.effectivePermissions['execution.plan.approve'], 'DENY');
      expect(find.text('Đã lưu quyền'), findsNothing);

      // 3. Save thất bại do VERSION_CONFLICT
      mockService.shouldFailUpdate = true;
      final saveButton = find.byKey(const ValueKey('permission-save'));
      await tester.tap(saveButton);
      await tester.pumpAndSettle();

      // Kiểm tra widget lỗi có key permission-conflict hiển thị
      expect(find.byKey(const ValueKey('permission-conflict')), findsOneWidget);
      expect(find.textContaining('VERSION_CONFLICT'), findsOneWidget);
      expect(find.text('Đã lưu quyền'), findsNothing);

      // Form vẫn giữ nguyên draft
      expect(controller.draftRolePermissions['role-operator-1']?['execution.plan.approve'], 'ALLOW');

      // 4. Test simulation panel
      final simButton = find.text('Mô phỏng');
      await tester.ensureVisible(simButton);
      await tester.tap(simButton);
      await tester.pumpAndSettle();


      expect(find.textContaining('Kết quả phân tích quyết định:'), findsOneWidget);
      expect(find.textContaining('Rule requires approval from founder'), findsOneWidget);
    },
  );
}
