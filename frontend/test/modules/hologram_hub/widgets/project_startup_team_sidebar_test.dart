import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/models/project_startup_team.dart';
import 'package:frontend/modules/hologram_hub/services/project_startup_team_service.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_startup_team_sidebar.dart';
import 'package:get/get.dart';

class FakeStartupTeamService extends ProjectStartupTeamService {
  String? lastActivatedProfileKey;
  int? lastActivatedExpectedVersion;
  String? lastPausedProfileKey;
  int? lastPausedExpectedVersion;

  @override
  Future<ApiResult<ProjectStartupTeamMember>> activateMember({
    required String projectId,
    required String profileKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    lastActivatedProfileKey = profileKey;
    lastActivatedExpectedVersion = expectedVersion;
    return ApiSuccess(
      data: ProjectStartupTeamMember(
        profileKey: profileKey,
        label: profileKey,
        displayState: TeamDisplayState.active,
        runtimeReadiness: RuntimeReadiness.ready,
        assignmentVersion: expectedVersion + 1,
        activatedAt: DateTime.parse('2026-09-11T12:00:00Z'),
      ),
      meta: ApiResponseMeta(
        dataState: ApiDataState.populated,
        observedAt: DateTime.now(),
      ),
    );
  }

  @override
  Future<ApiResult<ProjectStartupTeamMember>> pauseMember({
    required String projectId,
    required String profileKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    lastPausedProfileKey = profileKey;
    lastPausedExpectedVersion = expectedVersion;
    return ApiSuccess(
      data: ProjectStartupTeamMember(
        profileKey: profileKey,
        label: profileKey,
        displayState: TeamDisplayState.paused,
        runtimeReadiness: RuntimeReadiness.ready,
        assignmentVersion: expectedVersion + 1,
      ),
      meta: ApiResponseMeta(
        dataState: ApiDataState.populated,
        observedAt: DateTime.now(),
      ),
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FounderCommandCenterController controller;
  late FakeStartupTeamService fakeService;

  final test9Profiles = [
    const ProjectStartupTeamMember(
      profileKey: 'founder_assistant',
      label: 'Co-Founder',
      displayState: TeamDisplayState.chatReady,
      runtimeReadiness: RuntimeReadiness.ready,
    ),
    const ProjectStartupTeamMember(
      profileKey: 'research_intelligence',
      label: 'Research & Intelligence',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.ready,
      assignmentVersion: 1,
    ),
    const ProjectStartupTeamMember(
      profileKey: 'strategy',
      label: 'Strategy',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.ready,
      assignmentVersion: 1,
    ),
    ProjectStartupTeamMember(
      profileKey: 'marketing',
      label: 'Marketing',
      displayState: TeamDisplayState.active,
      runtimeReadiness: RuntimeReadiness.ready,
      assignmentVersion: 2,
      activatedAt: DateTime.parse('2026-09-11T10:00:00Z'),
      activatedBy: 'founder-1',
    ),
    const ProjectStartupTeamMember(
      profileKey: 'finance',
      label: 'Finance',
      displayState: TeamDisplayState.paused,
      runtimeReadiness: RuntimeReadiness.ready,
      assignmentVersion: 3,
    ),
    const ProjectStartupTeamMember(
      profileKey: 'crm',
      label: 'CRM',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.pendingCrmFoundation,
      disabledReason: 'Cần tích hợp CRM trước khi kích hoạt',
    ),
    const ProjectStartupTeamMember(
      profileKey: 'sales',
      label: 'Sales',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.pendingCrmFoundation,
      disabledReason: 'Cần tích hợp CRM trước khi kích hoạt',
    ),
    const ProjectStartupTeamMember(
      profileKey: 'coding',
      label: 'Coding',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.deferredCoding,
      disabledReason: 'Tính năng lập trình chưa mở trong giai đoạn hiện tại',
    ),
    const ProjectStartupTeamMember(
      profileKey: 'customer_support',
      label: 'Customer Support',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.pendingProjectKnowledge,
      disabledReason: 'Cần cấu hình tài liệu và tri thức dự án',
    ),
  ];

  setUp(() {
    Get.testMode = true;
    fakeService = FakeStartupTeamService();
    controller = FounderCommandCenterController(startupTeamService: fakeService);
    controller.activeProjectId.value = 'proj-123';
    controller.activeProjectTitle.value = 'Alpha B2B Project';
    controller.startupTeam.assignAll(test9Profiles);
  });

  tearDown(() {
    Get.reset();
  });

  Widget buildTestWidget({VoidCallback? onOpenCofounderChat}) {
    return GetMaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: SizedBox(
            width: 400,
            child: ProjectStartupTeamSidebar(
              controller: controller,
              shrinkWrap: true,
              onOpenCofounderChat: onOpenCofounderChat ?? () {},
            ),
          ),
        ),
      ),
    );
  }

  testWidgets('renders all 9 profiles truthful to catalog and truthful badges',
      (tester) async {
    await tester.pumpWidget(buildTestWidget());
    await tester.pumpAndSettle();

    // Verify header
    expect(find.text('ĐỘI NGŨ KHỞI NGHIỆP'), findsOneWidget);
    expect(find.textContaining('Alpha B2B Project (2/9 đang chạy)'), findsOneWidget);

    // Verify all 9 profile labels exist in the widget tree
    expect(find.text('Co-Founder'), findsOneWidget);
    expect(find.text('Research & Intelligence'), findsOneWidget);
    expect(find.text('Strategy'), findsOneWidget);
    expect(find.text('Marketing'), findsOneWidget);
    expect(find.text('Finance'), findsOneWidget);
    expect(find.text('CRM'), findsOneWidget);
    expect(find.text('Sales'), findsOneWidget);
    expect(find.text('Coding'), findsOneWidget);
    expect(find.text('Customer Support'), findsOneWidget);

    // Verify truthful badges
    expect(find.text('Co-Founder chat ready'), findsOneWidget);
    expect(find.text('Active'), findsOneWidget);
    expect(find.text('Tạm dừng'), findsNWidgets(2)); // 1 badge for Finance, 1 button for Marketing
    expect(find.text('Coming later'), findsWidgets);
    expect(find.text('Cần tích hợp CRM'), findsWidgets);
    expect(find.text('Cần tri thức dự án'), findsWidgets);
    expect(find.text('Sẵn sàng'), findsNWidgets(2)); // Research & Intelligence, Strategy
  });

  testWidgets('activate button triggers controller action with expected version',
      (tester) async {
    await tester.pumpWidget(buildTestWidget());
    await tester.pumpAndSettle();

    final activateResearchBtn = find.byKey(const Key('btn_activate_research_intelligence'));
    expect(activateResearchBtn, findsOneWidget);

    await tester.tap(activateResearchBtn);
    await tester.pumpAndSettle();

    expect(fakeService.lastActivatedProfileKey, equals('research_intelligence'));
    expect(fakeService.lastActivatedExpectedVersion, equals(1));
  });

  testWidgets('coding shows Coming later and cannot be activated', (tester) async {
    await tester.pumpWidget(buildTestWidget());
    await tester.pumpAndSettle();

    // The coding button must be disabled
    final codingBtnFinder = find.byKey(const Key('btn_disabled_coding'));
    expect(codingBtnFinder, findsOneWidget);

    final buttonWidget = tester.widget<OutlinedButton>(codingBtnFinder);
    expect(buttonWidget.onPressed, isNull);
    expect(find.byKey(const Key('btn_activate_coding')), findsNothing);
  });

  testWidgets('CRM shows Cần tích hợp CRM and cannot be activated', (tester) async {
    await tester.pumpWidget(buildTestWidget());
    await tester.pumpAndSettle();

    // The CRM button must be disabled
    final crmBtnFinder = find.byKey(const Key('btn_disabled_crm'));
    expect(crmBtnFinder, findsOneWidget);

    final buttonWidget = tester.widget<OutlinedButton>(crmBtnFinder);
    expect(buttonWidget.onPressed, isNull);
    expect(find.byKey(const Key('btn_activate_crm')), findsNothing);
  });

  testWidgets('Co-Founder button triggers onOpenCofounderChat callback', (tester) async {
    bool chatOpened = false;
    await tester.pumpWidget(buildTestWidget(
      onOpenCofounderChat: () {
        chatOpened = true;
      },
    ));
    await tester.pumpAndSettle();

    final chatBtn = find.byKey(const Key('btn_chat_cofounder'));
    expect(chatBtn, findsOneWidget);

    await tester.tap(chatBtn);
    await tester.pumpAndSettle();

    expect(chatOpened, isTrue);
  });
}
