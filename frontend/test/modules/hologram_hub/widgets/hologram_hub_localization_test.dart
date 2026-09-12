import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/locale_cache.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/models/project_startup_team.dart';
import 'package:frontend/modules/hologram_hub/services/project_startup_team_service.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_startup_team_sidebar.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_operating_week_card.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_context_bar.dart';

class _FakeStartupTeamService extends ProjectStartupTeamService {}

class _FakeLocaleCache implements LocaleCache {
  SupportedLocale? _val;
  _FakeLocaleCache([String? initial])
      : _val = initial != null ? SupportedLocaleWire.parse(initial) : null;

  @override
  Future<SupportedLocale?> read() async => _val;

  @override
  Future<void> write(SupportedLocale locale) async {
    _val = locale;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late LocaleController localeController;
  late FounderCommandCenterController commandCenterController;

  final sampleMembers = <ProjectStartupTeamMember>[
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
    ),
    const ProjectStartupTeamMember(
      profileKey: 'crm',
      label: 'CRM',
      displayState: TeamDisplayState.template,
      runtimeReadiness: RuntimeReadiness.pendingCrmFoundation,
    ),
  ];

  setUp(() {
    Get.reset();
    Get.testMode = true;
    localeController = Get.put<LocaleController>(
      LocaleController(cache: _FakeLocaleCache('vi-VN')),
      permanent: true,
    );
    commandCenterController = FounderCommandCenterController(
      startupTeamService: _FakeStartupTeamService(),
    );
    commandCenterController.activeProjectId.value = 'proj-loc';
    commandCenterController.activeProjectTitle.value = 'COSA';
    commandCenterController.startupTeam.assignAll(sampleMembers);
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('ProjectStartupTeamSidebar renders English text when enUS is active', (tester) async {
    localeController.setLocale(SupportedLocale.enUS);

    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('en', 'US'),
        home: Scaffold(
          body: SingleChildScrollView(
            child: SizedBox(
              width: 400,
              child: ProjectStartupTeamSidebar(
                controller: commandCenterController,
                shrinkWrap: true,
                onOpenCofounderChat: () {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // English Header
    expect(find.text('STARTUP TEAM'), findsOneWidget);
    expect(find.textContaining('COSA (1/3 running)'), findsOneWidget);

    // English Badges
    expect(find.text('Co-Founder chat ready'), findsOneWidget);
    expect(find.text('Ready'), findsOneWidget);
    expect(find.text('Needs CRM Integration'), findsOneWidget);

    // English Co-Founder button
    expect(find.text('Open Co-Founder Chat'), findsOneWidget);
  });

  testWidgets('ProjectStartupTeamSidebar renders Vietnamese text when viVN is active', (tester) async {
    localeController.setLocale(SupportedLocale.viVN);

    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('vi', 'VN'),
        home: Scaffold(
          body: SingleChildScrollView(
            child: SizedBox(
              width: 400,
              child: ProjectStartupTeamSidebar(
                controller: commandCenterController,
                shrinkWrap: true,
                onOpenCofounderChat: () {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Vietnamese Header
    expect(find.text('ĐỘI NGŨ KHỞI NGHIỆP'), findsOneWidget);
    expect(find.textContaining('COSA (1/3 đang chạy)'), findsOneWidget);

    // Vietnamese Badges
    expect(find.text('Sẵn sàng'), findsOneWidget);
    expect(find.text('Cần tích hợp CRM'), findsOneWidget);

    // Vietnamese Co-Founder button
    expect(find.text('Mở Chat Co-Founder'), findsOneWidget);
  });

  testWidgets('ProjectOperatingWeekCard renders English and Vietnamese based on locale', (tester) async {
    // 1. English
    localeController.setLocale(SupportedLocale.enUS);
    await tester.pumpWidget(
      const GetMaterialApp(
        locale: Locale('en', 'US'),
        home: Scaffold(
          body: ProjectOperatingWeekCard(
            operatingLoop: null,
            isLoading: false,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Project Operating Cycle'), findsOneWidget);
    expect(find.text('No active operating cycle for this project.'), findsOneWidget);

    // 2. Vietnamese
    localeController.setLocale(SupportedLocale.viVN);
    await tester.pumpWidget(
      const GetMaterialApp(
        locale: Locale('vi', 'VN'),
        home: Scaffold(
          body: ProjectOperatingWeekCard(
            operatingLoop: null,
            isLoading: false,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Chu kỳ hoạt động dự án'), findsOneWidget);
    expect(
      find.text('Dự án chưa có chu kỳ hoạt động (Operating Cycle) nào đang diễn ra.'),
      findsOneWidget,
    );
  });

  testWidgets('ProjectContextBar renders formatted stage in English vs Vietnamese', (tester) async {
    final selectedProjectId = Rx<String?>('proj-cosa');
    final projects = [
      {'id': 'proj-cosa', 'title': 'COSA', 'lifecycleStage': 'P0_DISCOVERY'},
    ];

    // 1. English
    localeController.setLocale(SupportedLocale.enUS);
    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('en', 'US'),
        home: Scaffold(
          body: ProjectContextBar(
            projects: projects,
            selectedProjectId: selectedProjectId,
            onSelected: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('P0: Discovery'), findsOneWidget);

    // 2. Vietnamese
    localeController.setLocale(SupportedLocale.viVN);
    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('vi', 'VN'),
        home: Scaffold(
          body: ProjectContextBar(
            projects: projects,
            selectedProjectId: selectedProjectId,
            onSelected: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('P0: Khám phá cơ hội'), findsOneWidget);
  });
}
