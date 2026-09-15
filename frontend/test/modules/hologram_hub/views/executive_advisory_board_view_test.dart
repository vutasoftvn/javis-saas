import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/executive_advisory_board_controller.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/views/executive_advisory_board_view.dart';

ExecutiveAdvisorRole _role() => const ExecutiveAdvisorRole(
  roleKey: 'cfo', label: 'CFO Advisor', advisoryRemit: 'Cash runway',
  requiredProfileKey: 'finance', officeState: ExecutiveOfficeState.active,
  projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
  stageEligibility: ExecutiveStageEligibility.allowed,
  effectiveState: ExecutiveEffectiveState.deploymentInactive,
  workspaceOfficeVersion: 2,
);

ExecutiveAdvisorRole _availableOfficeRole() => const ExecutiveAdvisorRole(
  roleKey: 'cfo', label: 'CFO Advisor', advisoryRemit: 'Cash runway',
  requiredProfileKey: 'finance',
  officeState: ExecutiveOfficeState.availableNotActivated,
  projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
  stageEligibility: ExecutiveStageEligibility.allowed,
  effectiveState: ExecutiveEffectiveState.officeDisabled,
  workspaceOfficeVersion: 1,
);

void main() {
  tearDown(Get.reset);
  testWidgets('active Workspace office without Project deployment is not shown as Project active', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.roles.assignAll([_role()]);
    await tester.pumpWidget(GetMaterialApp(home: Scaffold(body: ExecutiveAdvisoryBoardView(
      projectId: 'proj-1', workspaceId: 'ws-1', controller: controller,
    ))));
    expect(find.text('Role đã bật ở Workspace — cần deploy Agent vào Project'), findsOneWidget);
    expect(find.text('Cần deploy Agent'), findsOneWidget);
    expect(find.text('Đang hoạt động'), findsNothing);
  });
  testWidgets('UNAVAILABLE office has no Enable Office action', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.roles.assignAll([const ExecutiveAdvisorRole(
      roleKey: 'cfo', label: 'CFO', advisoryRemit: 'Cash', requiredProfileKey: 'finance',
      officeState: ExecutiveOfficeState.unavailable, projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
      stageEligibility: ExecutiveStageEligibility.allowed, effectiveState: ExecutiveEffectiveState.officeDisabled,
      workspaceOfficeVersion: 1, disabledReason: 'UNDERLYING_PROFILE_UNAVAILABLE',
    )]);
    await tester.pumpWidget(GetMaterialApp(home: Scaffold(body: ExecutiveAdvisoryBoardView(projectId: 'p', workspaceId: 'w', controller: controller))));
    expect(find.text('Bật Office'), findsNothing);
    expect(find.text('UNDERLYING_PROFILE_UNAVAILABLE'), findsOneWidget);
  });

  testWidgets('server-confirmed available Office can be enabled', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.roles.assignAll([_availableOfficeRole()]);
    await tester.pumpWidget(GetMaterialApp(home: Scaffold(body: ExecutiveAdvisoryBoardView(
      projectId: 'p', workspaceId: 'w', controller: controller,
    ))));
    expect(find.text('Bật Office'), findsOneWidget);
  });
}
