import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/hologram_hub/controllers/executive_advisory_board_controller.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/services/executive_advisory_board_service.dart';
import 'package:frontend/modules/hologram_hub/views/executive_advisory_board_view.dart';

class _BoardService extends ExecutiveAdvisoryBoardService {
  final List<ExecutiveAdvisorRole> response;

  _BoardService(this.response);

  @override
  Future<ApiResult<List<ExecutiveAdvisorRole>>> fetchRoles(
    String projectId,
  ) async => ApiSuccess(data: response, meta: _meta());
}

ApiResponseMeta _meta() => ApiResponseMeta(
  dataState: ApiDataState.populated,
  observedAt: DateTime.parse('2026-09-15T00:00:00Z'),
  sources: const [],
);

ExecutiveAdvisorRole _role() => const ExecutiveAdvisorRole(
  roleKey: 'cfo',
  label: 'CFO Advisor',
  advisoryRemit: 'Cash runway',
  requiredProfileKey: 'finance',
  officeState: ExecutiveOfficeState.active,
  projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
  stageEligibility: ExecutiveStageEligibility.allowed,
  effectiveState: ExecutiveEffectiveState.deploymentInactive,
  workspaceOfficeVersion: 2,
  workspaceAgentId: 'agent-1',
);

ExecutiveAdvisorRole _availableOfficeRole() => const ExecutiveAdvisorRole(
  roleKey: 'cfo',
  label: 'CFO Advisor',
  advisoryRemit: 'Cash runway',
  requiredProfileKey: 'finance',
  officeState: ExecutiveOfficeState.availableNotActivated,
  projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
  stageEligibility: ExecutiveStageEligibility.allowed,
  effectiveState: ExecutiveEffectiveState.officeDisabled,
  workspaceOfficeVersion: 1,
);

ExecutiveAdvisorRole _otherStageRole() => const ExecutiveAdvisorRole(
  roleKey: 'ciso',
  label: 'Chief Information Security Officer',
  advisoryRemit: 'Security',
  requiredProfileKey: 'security',
  officeState: ExecutiveOfficeState.unavailable,
  projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
  stageEligibility: ExecutiveStageEligibility.notSuggested,
  effectiveState: ExecutiveEffectiveState.officeDisabled,
  workspaceOfficeVersion: 1,
  disabledReason: 'UNDERLYING_PROFILE_UNAVAILABLE',
);

ExecutiveDeliberation _deliberation(String state) => ExecutiveDeliberation(
  id: 'delib-1',
  workspaceId: 'ws-1',
  projectId: 'proj-1',
  title: 'Pricing',
  state: state,
  activeFrameVersion: 1,
  version: 3,
  createdBy: 'u-1',
  createdAt: DateTime.parse('2026-09-25T00:00:00Z'),
  updatedAt: DateTime.parse('2026-09-25T00:00:00Z'),
);

Widget _board(ExecutiveAdvisoryBoardController controller) => GetMaterialApp(
  home: Scaffold(
    body: ExecutiveAdvisoryBoardView(
      projectId: 'proj-1',
      workspaceId: 'ws-1',
      controller: controller,
    ),
  ),
);

void main() {
  tearDown(Get.reset);

  testWidgets('opening Board loads and renders Project advisor roles', (
    tester,
  ) async {
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([_role()]),
    );

    await tester.pumpWidget(_board(controller));
    await tester.pump();

    expect(find.text('CFO Advisor'), findsOneWidget);
  });

  testWidgets(
    'shows roles recommended for the current stage before other roles',
    (tester) async {
      final controller = ExecutiveAdvisoryBoardController(
        service: _BoardService([_role(), _otherStageRole()]),
      );

      await tester.pumpWidget(_board(controller));
      await tester.pump();

      expect(find.text('Đề xuất cho giai đoạn hiện tại'), findsOneWidget);
      expect(find.text('Các role khác'), findsOneWidget);
      expect(
        tester.getTopLeft(find.text('CFO Advisor')).dy,
        lessThan(
          tester.getTopLeft(find.text('Chief Information Security Officer')).dy,
        ),
      );
    },
  );

  testWidgets('shows an empty state when Board has no roles to display', (
    tester,
  ) async {
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService(const []),
    );

    await tester.pumpWidget(_board(controller));
    await tester.pump();

    expect(find.text('Chưa có role cố vấn nào để hiển thị.'), findsOneWidget);
  });

  testWidgets('unavailable underlying profile offers the Founder setup step', (
    tester,
  ) async {
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([_otherStageRole()]),
    );
    await tester.pumpWidget(_board(controller));
    await tester.pump();

    expect(find.text('Kích hoạt agent nền'), findsOneWidget);
  });

  testWidgets(
    'role status is conveyed by an icon with an explanatory tooltip',
    (tester) async {
      final controller = ExecutiveAdvisoryBoardController(
        service: _BoardService([_role()]),
      );
      await tester.pumpWidget(_board(controller));
      await tester.pump();

    expect(find.byIcon(Icons.cloud_upload_outlined), findsNWidgets(2));
      expect(find.byType(Tooltip), findsWidgets);
      expect(find.text('Cần deploy Agent'), findsNothing);
    },
  );

  testWidgets(
    'active Workspace office without Project deployment is not shown as Project active',
    (tester) async {
      final controller = ExecutiveAdvisoryBoardController(
        service: _BoardService([_role()]),
      );
      await tester.pumpWidget(_board(controller));
      await tester.pump();
      expect(
        find.text('Role đã bật ở Workspace — cần deploy Agent vào Project'),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.cloud_upload_outlined), findsNWidgets(2));
      expect(find.text('Deploy Agent'), findsOneWidget);
      expect(find.text('Đang hoạt động'), findsNothing);
    },
  );
  testWidgets('UNAVAILABLE office has no Enable Office action', (tester) async {
    final unavailableRole = const ExecutiveAdvisorRole(
      roleKey: 'cfo',
      label: 'CFO',
      advisoryRemit: 'Cash',
      requiredProfileKey: 'finance',
      officeState: ExecutiveOfficeState.unavailable,
      projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
      stageEligibility: ExecutiveStageEligibility.allowed,
      effectiveState: ExecutiveEffectiveState.officeDisabled,
      workspaceOfficeVersion: 1,
      disabledReason: 'UNDERLYING_PROFILE_UNAVAILABLE',
    );
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([unavailableRole]),
    );
    await tester.pumpWidget(_board(controller));
    await tester.pump();
    expect(find.text('Bật Office'), findsNothing);
    expect(find.text('UNDERLYING_PROFILE_UNAVAILABLE'), findsOneWidget);
  });

  testWidgets('server-confirmed available Office can be enabled', (
    tester,
  ) async {
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([_availableOfficeRole()]),
    );
    await tester.pumpWidget(_board(controller));
    await tester.pump();
    expect(find.text('Bật Office'), findsOneWidget);
  });

  testWidgets('shows one P0 Core repair action only when authorized by server', (
    tester,
  ) async {
    const repairableRole = ExecutiveAdvisorRole(
      roleKey: 'cfo',
      label: 'CFO',
      advisoryRemit: 'Cash',
      requiredProfileKey: 'finance',
      officeState: ExecutiveOfficeState.unavailable,
      projectDeploymentState: ExecutiveProjectDeploymentState.inactive,
      stageEligibility: ExecutiveStageEligibility.allowed,
      effectiveState: ExecutiveEffectiveState.officeDisabled,
      workspaceOfficeVersion: 1,
      p0CoreBootstrapAvailable: true,
    );
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([repairableRole]),
    );

    await tester.pumpWidget(_board(controller));
    await tester.pump();

    expect(find.text('Khởi tạo P0 Core'), findsOneWidget);
  });

  for (final state in ['AWAITING_FOUNDER', 'CRITIC_REVIEW']) {
    testWidgets('decision actions are shown for $state', (tester) async {
      final controller = ExecutiveAdvisoryBoardController(
        service: _BoardService([_role()]),
      );
      await tester.pumpWidget(_board(controller));
      await tester.pump();
      controller.currentDeliberation.value = _deliberation(state);
      await tester.pump();

      expect(find.text('Phê duyệt (Approve)'), findsOneWidget);
      expect(find.text('Huỷ bỏ'), findsOneWidget);
    });
  }

  testWidgets('decision actions are hidden while analysis is running', (
    tester,
  ) async {
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([_role()]),
    );
    await tester.pumpWidget(_board(controller));
    await tester.pump();
    controller.currentDeliberation.value = _deliberation('ANALYZING');
    await tester.pump();

    expect(find.text('Phê duyệt (Approve)'), findsNothing);
  });

  testWidgets('FAILED_REQUIRES_ATTENTION offers cancel but no approval', (
    tester,
  ) async {
    final controller = ExecutiveAdvisoryBoardController(
      service: _BoardService([_role()]),
    );
    await tester.pumpWidget(_board(controller));
    await tester.pump();
    controller.currentDeliberation.value = _deliberation(
      'FAILED_REQUIRES_ATTENTION',
    );
    await tester.pump();

    expect(find.text('Phê duyệt (Approve)'), findsNothing);
    expect(find.text('Huỷ bỏ'), findsOneWidget);
    expect(
      find.text(
        'Không cố vấn nào trả được phân tích. Huỷ, hoặc đóng khung lại câu hỏi.',
      ),
      findsOneWidget,
    );
  });
}
