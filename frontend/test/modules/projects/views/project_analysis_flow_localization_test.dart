import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/projects/controllers/project_analysis_flow_controller.dart';
import 'package:frontend/modules/projects/models/stage_analysis_models.dart';
import 'package:frontend/modules/projects/views/project_analysis_flow_view.dart';

void main() {
  setUp(() {
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  group('StageAnalysisKnowledge Localization', () {
    test('returns Vietnamese template when lang is vi', () {
      final tpl = StageAnalysisKnowledge.getTemplate(ProjectStage.p0Discovery, 'vi');
      expect(tpl.customerHint, contains('Founder startup B2B SaaS'));
      expect(tpl.problemHint, contains('OKR'));
      expect(tpl.focusHeadline, contains('Early Adopter'));
      expect(tpl.coreAssumptions, isNotEmpty);

      final tplP1 = StageAnalysisKnowledge.getTemplate(ProjectStage.p1ProblemValidation, 'vi');
      expect(tplP1.customerHint, contains('Trưởng phòng Marketing'));
      expect(tplP1.problemHint, contains('Chi phí chạy ads'));
    });

    test('returns English template when lang is en', () {
      final tpl = StageAnalysisKnowledge.getTemplate(ProjectStage.p0Discovery, 'en');
      expect(tpl.customerHint, contains('Founder of B2B SaaS'));
      expect(tpl.problemHint, contains('OKR'));
      expect(tpl.focusHeadline, contains('early adopters'));
      expect(tpl.coreAssumptions, isNotEmpty);

      final tplP1 = StageAnalysisKnowledge.getTemplate(ProjectStage.p1ProblemValidation, 'en');
      expect(tplP1.customerHint, contains('Marketing Director'));
      expect(tplP1.problemHint, contains('Rising ad spend'));
    });
  });

  group('ProjectAnalysisFlowController Localization', () {
    test('uses English defaults, AI suggestions, and validations when locale is enUS', () async {
      final lc = Get.put(LocaleController());
      lc.current.value = SupportedLocale.enUS;

      final controller = Get.put(
        ProjectAnalysisFlowController(
          projectId: 'proj-123',
          projectTitle: 'AI Co-Founder',
          initialStage: ProjectStage.p0Discovery,
        ),
        tag: 'test_en',
      );

      expect(controller.isEnglish, isTrue);
      expect(controller.guidance.customerHint, contains('Founder of B2B SaaS'));

      // Step 0 validation in English
      expect(controller.validateCurrentStep(), isFalse);
      expect(controller.errorMessage.value, equals('Please enter your target customer / ICP.'));

      controller.targetCustomerCtrl.text = 'Early-stage Startup Founders';
      expect(controller.validateCurrentStep(), isFalse);
      expect(controller.errorMessage.value, equals('Please describe the core problem or pain point your project solves.'));

      controller.problemStatementCtrl.text = 'Struggling with legal and financial structure';
      expect(controller.validateCurrentStep(), isTrue);

      // AI Suggestions in English
      await controller.generateAiSuggestions();
      expect(controller.firstWeekOutcomeCtrl.text, contains('[P0 - Discovery & Opportunity Evaluation]'));
      expect(controller.firstWeekOutcomeCtrl.text, contains('Validate solution for "Early-stage Startup Founders"'));
      expect(controller.firstWeekActions.first, contains('Build target list of 10 matching customers'));
    });

    test('uses Vietnamese defaults, AI suggestions, and validations when locale is viVN', () async {
      final lc = Get.put(LocaleController());
      lc.current.value = SupportedLocale.viVN;

      final controller = Get.put(
        ProjectAnalysisFlowController(
          projectId: 'proj-456',
          projectTitle: 'Startup VN',
          initialStage: ProjectStage.p0Discovery,
        ),
        tag: 'test_vi',
      );

      expect(controller.isEnglish, isFalse);
      expect(controller.guidance.customerHint, contains('Founder startup B2B SaaS'));

      // Step 0 validation in Vietnamese
      expect(controller.validateCurrentStep(), isFalse);
      expect(controller.errorMessage.value, equals('Vui lòng nhập đối tượng khách hàng mục tiêu.'));

      controller.targetCustomerCtrl.text = 'Founder SME';
      controller.problemStatementCtrl.text = 'Thiếu nhân sự và vốn';
      expect(controller.validateCurrentStep(), isTrue);

      // AI Suggestions in Vietnamese
      await controller.generateAiSuggestions();
      expect(controller.firstWeekOutcomeCtrl.text, contains('[P0 - Khám phá & Đánh giá cơ hội]'));
      expect(controller.firstWeekOutcomeCtrl.text, contains('Xác thực giải pháp cho "Founder SME"'));
      expect(controller.firstWeekActions.first, contains('Lập danh sách 10 khách hàng mục tiêu phù hợp'));
    });
  });

  group('ProjectAnalysisFlowView Widget Localization', () {
    testWidgets('renders English UI texts when LocaleController is enUS', (tester) async {
      final lc = Get.put(LocaleController());
      lc.current.value = SupportedLocale.enUS;

      await tester.pumpWidget(
        const GetMaterialApp(
          home: ProjectAnalysisFlowView(
            projectId: 'proj-en-ui',
            projectTitle: 'Global Venture',
            initialStage: 'P0_DISCOVERY',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Analysis & Plan Proposal: Global Venture'), findsOneWidget);
      expect(find.text('Customer & Problem'), findsOneWidget);
      expect(find.text('Step 1: Target Customer & Core Problem'), findsOneWidget);
      expect(find.text('Continue'), findsOneWidget);
    });

    testWidgets('renders Vietnamese UI texts when LocaleController is viVN', (tester) async {
      final lc = Get.put(LocaleController());
      lc.current.value = SupportedLocale.viVN;

      await tester.pumpWidget(
        const GetMaterialApp(
          home: ProjectAnalysisFlowView(
            projectId: 'proj-vi-ui',
            projectTitle: 'Dự án Việt',
            initialStage: 'P0_DISCOVERY',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Phân tích & Đề xuất Kế hoạch: Dự án Việt'), findsOneWidget);
      expect(find.text('Khách hàng & Nỗi đau'), findsOneWidget);
      expect(find.text('Bước 1: Chân dung Khách hàng & Vấn đề Cốt lõi'), findsOneWidget);
      expect(find.text('Tiếp tục bước sau'), findsOneWidget);
    });
  });
}
