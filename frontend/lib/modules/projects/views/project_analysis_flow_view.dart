import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/models/stage_model.dart';
import '../controllers/project_analysis_flow_controller.dart';

class ProjectAnalysisFlowView extends StatelessWidget {
  final String projectId;
  final String projectTitle;
  final String? initialStage;

  const ProjectAnalysisFlowView({
    super.key,
    required this.projectId,
    required this.projectTitle,
    this.initialStage,
  });

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    final parsedStage = ProjectStage.fromString(initialStage);
    final tag = 'analysis_$projectId';

    final controller = Get.put(
      ProjectAnalysisFlowController(
        projectId: projectId,
        projectTitle: projectTitle,
        initialStage: parsedStage,
      ),
      tag: tag,
    );

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white70),
          onPressed: () => Get.back(),
        ),
        title: Obx(() {
          final isEn = _isEnglish();
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isEn
                    ? 'Analysis & Plan Proposal: $projectTitle'
                    : 'Phân tích & Đề xuất Kế hoạch: $projectTitle',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              Text(
                isEn
                    ? 'Set first-week execution objectives based on project stage'
                    : 'Thiết lập mục tiêu thực thi tuần đầu căn cứ theo từng giai đoạn',
                style: const TextStyle(fontSize: 11, color: Colors.white54),
              ),
            ],
          );
        }),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: Obx(() {
            final isEn = _isEnglish();
            final step = controller.currentStep.value;

            return Column(
              children: [
                // Step Indicator Header
                _buildStepHeader(controller, isEn),

                if (controller.errorMessage.value != null)
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF3B1818),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.redAccent.withValues(alpha: 0.5)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            controller.errorMessage.value!,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                          ),
                        ),
                      ],
                    ),
                  ),

                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                    child: switch (step) {
                      0 => _buildStep1CustomerProblem(controller, isEn),
                      1 => _buildStep2StageAssumptions(controller, isEn),
                      2 => _buildStep3FirstWeekPlan(controller, isEn),
                      _ => const SizedBox.shrink(),
                    },
                  ),
                ),

                // Bottom Action Navigation Bar
                _buildBottomBar(controller, isEn),
              ],
            );
          }),
        ),
      ),
    );
  }

  Widget _buildStepHeader(ProjectAnalysisFlowController controller, bool isEn) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      margin: const EdgeInsets.only(bottom: 8),
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: constraints.maxWidth),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildStepCircle(
                    0,
                    '1',
                    isEn ? 'Customer & Problem' : 'Khách hàng & Nỗi đau',
                    controller.currentStep.value,
                  ),
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 12),
                    width: 32,
                    height: 2,
                    color: controller.currentStep.value >= 1 ? const Color(0xFF6366F1) : const Color(0xFF334155),
                  ),
                  _buildStepCircle(
                    1,
                    '2',
                    isEn ? 'Stage & Assumptions' : 'Giai đoạn & Giả định',
                    controller.currentStep.value,
                  ),
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 12),
                    width: 32,
                    height: 2,
                    color: controller.currentStep.value >= 2 ? const Color(0xFF6366F1) : const Color(0xFF334155),
                  ),
                  _buildStepCircle(
                    2,
                    '3',
                    isEn ? 'Outcome & Weekly Plan' : 'Outcome & Kế hoạch tuần',
                    controller.currentStep.value,
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildStepCircle(
    int stepIndex,
    String number,
    String title,
    int currentStep,
  ) {
    final isActive = currentStep == stepIndex;
    final isDone = currentStep > stepIndex;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isDone
                ? const Color(0xFF10B981)
                : (isActive ? const Color(0xFF6366F1) : const Color(0xFF1E293B)),
            border: Border.all(
              color: isActive ? const Color(0xFFA5B4FC) : const Color(0xFF334155),
              width: 1.5,
            ),
          ),
          child: Center(
            child: isDone
                ? const Icon(Icons.check, size: 16, color: Colors.white)
                : Text(
                    number,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: isActive ? Colors.white : Colors.white54,
                    ),
                  ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
            color: isActive ? Colors.white : (isDone ? Colors.white70 : Colors.white38),
          ),
        ),
      ],
    );
  }

  // --- STEP 1: CUSTOMER & PROBLEM STATEMENT ---
  Widget _buildStep1CustomerProblem(ProjectAnalysisFlowController controller, bool isEn) {
    final tpl = controller.guidance;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionCard(
          title: isEn
              ? 'Step 1: Target Customer & Core Problem'
              : 'Bước 1: Chân dung Khách hàng & Vấn đề Cốt lõi',
          description: isEn
              ? 'All subsequent analysis and action recommendations will focus on the target customer and pain points you define here.'
              : 'Mọi phân tích và đề xuất hành động về sau đều sẽ xoay quanh đối tượng và nỗi đau bạn nhập tại đây.',
          icon: Icons.person_search_outlined,
          iconColor: const Color(0xFF6366F1),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isEn
                    ? 'Target Customer (Target Customer / ICP)'
                    : 'Khách hàng mục tiêu (Target Customer / ICP)',
                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white, fontSize: 13.5),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: controller.targetCustomerCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 13.5),
                decoration: InputDecoration(
                  hintText: tpl.customerHint,
                  hintStyle: const TextStyle(color: Colors.white38, fontSize: 13),
                  filled: true,
                  fillColor: const Color(0xFF1E293B),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF334155))),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF6366F1))),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                isEn
                    ? 'Core Problem / Pain Point (Core Problem Statement)'
                    : 'Vấn đề / Nỗi đau nhức nhối nhất (Core Problem Statement)',
                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white, fontSize: 13.5),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: controller.problemStatementCtrl,
                maxLines: 3,
                style: const TextStyle(color: Colors.white, fontSize: 13.5),
                decoration: InputDecoration(
                  hintText: tpl.problemHint,
                  hintStyle: const TextStyle(color: Colors.white38, fontSize: 13),
                  filled: true,
                  fillColor: const Color(0xFF1E293B),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF334155))),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF6366F1))),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // --- STEP 2: STAGE, EVIDENCE & ASSUMPTIONS (Chained from Step 1) ---
  Widget _buildStep2StageAssumptions(ProjectAnalysisFlowController controller, bool isEn) {
    final tpl = controller.guidance;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Summary context of Step 1
        _buildContextBanner(
          isEn ? 'Established Context:' : 'Ngữ cảnh đã xác lập:',
          isEn
              ? 'Customer: "${controller.targetCustomerCtrl.text}" • Problem: "${controller.problemStatementCtrl.text}"'
              : 'Khách hàng: "${controller.targetCustomerCtrl.text}" • Nỗi đau: "${controller.problemStatementCtrl.text}"',
        ),
        const SizedBox(height: 16),

        _buildSectionCard(
          title: isEn
              ? 'Step 2: Lifecycle Stage & Core Assumptions'
              : 'Bước 2: Giai đoạn Vòng đời & Giả định Cốt lõi',
          description: isEn
              ? 'Select the current stage of your project to receive strategic questions and corresponding validation assumptions.'
              : 'Chọn đúng giai đoạn dự án đang ở để nhận câu hỏi chiến lược và bộ giả định kiểm chứng tương ứng.',
          icon: Icons.alt_route_rounded,
          iconColor: const Color(0xFFA855F7),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isEn ? 'Current Project Stage:' : 'Giai đoạn hiện tại của Dự án:',
                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white, fontSize: 13.5),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: ProjectStage.values.map((s) {
                  final isSelected = controller.currentStage.value == s;
                  final stageLabel = isEn ? s.shortNameEn : s.shortNameVi;
                  return ChoiceChip(
                    label: Text('${s.code}: $stageLabel'),
                    selected: isSelected,
                    onSelected: (_) => controller.onStageChanged(s),
                    selectedColor: s.primaryColor.withValues(alpha: 0.3),
                    backgroundColor: const Color(0xFF1E293B),
                    side: BorderSide(color: isSelected ? s.primaryColor : const Color(0xFF334155)),
                    labelStyle: TextStyle(
                      color: isSelected ? Colors.white : Colors.white70,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      fontSize: 12,
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.tips_and_updates_outlined, color: Color(0xFFF59E0B), size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        tpl.focusHeadline,
                        style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 12.5, fontStyle: FontStyle.italic),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),
              Text(
                isEn
                    ? 'Core assumptions to validate in this stage (select or add new):'
                    : 'Các giả định cốt lõi cần kiểm chứng trong giai đoạn này (chọn hoặc thêm mới):',
                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white, fontSize: 13.5),
              ),
              const SizedBox(height: 10),

              ...tpl.coreAssumptions.map((assump) {
                final isChecked = controller.selectedAssumptions.contains(assump);
                return CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  value: isChecked,
                  activeColor: const Color(0xFFA855F7),
                  title: Text(assump, style: const TextStyle(color: Colors.white, fontSize: 13)),
                  onChanged: (_) => controller.toggleAssumption(assump),
                );
              }),

              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller.customAssumptionCtrl,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: isEn ? 'Add custom assumption...' : 'Thêm giả định khác...',
                        hintStyle: const TextStyle(color: Colors.white38, fontSize: 12.5),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF334155))),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => controller.addCustomAssumption(),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF334155), foregroundColor: Colors.white),
                    child: Text(isEn ? 'Add' : 'Thêm'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  // --- STEP 3: FIRST WEEK PLAN (Chained from Step 1 & Step 2) ---
  Widget _buildStep3FirstWeekPlan(ProjectAnalysisFlowController controller, bool isEn) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Summary context
        _buildContextBanner(
          isEn ? 'Chained Context:' : 'Kế thừa ngữ cảnh (Chained Context):',
          isEn
              ? 'Customer: ${controller.targetCustomerCtrl.text} • Stage: ${controller.currentStage.value.code} (${controller.selectedAssumptions.length} assumptions to validate)'
              : 'Khách hàng: ${controller.targetCustomerCtrl.text} • Giai đoạn: ${controller.currentStage.value.code} (${controller.selectedAssumptions.length} giả định đang kiểm chứng)',
        ),
        const SizedBox(height: 16),

        _buildSectionCard(
          title: isEn
              ? 'Step 3: First-Week Action Plan'
              : 'Bước 3: Kế hoạch Hành động Tuần Đầu tiên',
          description: isEn
              ? 'The AI engine suggests a key outcome and highest-priority actions for your first week based on previous steps.'
              : 'Hệ thống AI đề xuất Outcome then chốt và các hành động ưu tiên cao nhất cho tuần đầu căn cứ theo 2 bước trước.',
          icon: Icons.rocket_launch_outlined,
          iconColor: const Color(0xFF10B981),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    isEn
                        ? 'Key Outcome for Week 1:'
                        : 'Kết quả then chốt (Outcome) tuần đầu:',
                    style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white, fontSize: 13.5),
                  ),
                  TextButton.icon(
                    onPressed: controller.isAiGenerating.value ? null : () => controller.generateAiSuggestions(),
                    icon: controller.isAiGenerating.value
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)))
                        : const Icon(Icons.auto_awesome, size: 16, color: Color(0xFF10B981)),
                    label: Text(
                      isEn ? 'Regenerate with AI' : 'Gợi ý lại bằng AI',
                      style: const TextStyle(color: Color(0xFF10B981), fontSize: 12),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              TextField(
                controller: controller.firstWeekOutcomeCtrl,
                maxLines: 2,
                style: const TextStyle(color: Colors.white, fontSize: 13.5),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: const Color(0xFF1E293B),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF334155))),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF10B981))),
                ),
              ),

              const SizedBox(height: 20),
              Text(
                isEn
                    ? 'Top 1–3 Priority Actions (Tasks for Week 1):'
                    : 'Danh sách 1–3 Hành động ưu tiên (Tasks for Week 1):',
                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white, fontSize: 13.5),
              ),
              const SizedBox(height: 10),

              if (controller.firstWeekActions.isEmpty)
                Text(
                  isEn
                      ? 'No actions added yet. Enter custom tasks or use the AI suggestions above.'
                      : 'Chưa có hành động nào. Hãy nhập thêm hoặc dùng gợi ý AI bên trên.',
                  style: const TextStyle(color: Colors.white38, fontSize: 12.5),
                ),

              ...controller.firstWeekActions.asMap().entries.map((entry) {
                final idx = entry.key;
                final act = entry.value;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(color: const Color(0xFF10B981).withValues(alpha: 0.15), shape: BoxShape.circle),
                        child: const Icon(Icons.check_circle_outline, size: 16, color: Color(0xFF10B981)),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(act, style: const TextStyle(color: Colors.white, fontSize: 13)),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, size: 16, color: Colors.white38),
                        onPressed: () => controller.removeFirstWeekAction(idx),
                      ),
                    ],
                  ),
                );
              }),

              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller.newActionCtrl,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: isEn ? 'Add another action for Week 1...' : 'Thêm hành động khác cho tuần 1...',
                        hintStyle: const TextStyle(color: Colors.white38, fontSize: 12.5),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF334155))),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => controller.addFirstWeekAction(),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF334155), foregroundColor: Colors.white),
                    child: Text(isEn ? 'Add' : 'Thêm'),
                  ),
                ],
              ),

              const SizedBox(height: 20),
              const Divider(color: Color(0xFF334155)),
              const SizedBox(height: 10),
              Row(
                children: [
                  Text(
                    isEn
                        ? 'Operating Cycle Length:'
                        : 'Độ dài chu kỳ vận hành (Operating Cycle):',
                    style: const TextStyle(color: Colors.white70, fontSize: 12.5),
                  ),
                  const SizedBox(width: 12),
                  Obx(() => DropdownButton<int>(
                    value: controller.cycleDurationWeeks.value,
                    dropdownColor: const Color(0xFF1E293B),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    items: [1, 2, 3, 4, 6, 8, 12].map((w) {
                      return DropdownMenuItem<int>(
                        value: w,
                        child: Text(isEn ? '$w week${w > 1 ? 's' : ''}' : '$w tuần'),
                      );
                    }).toList(),
                    onChanged: (v) {
                      if (v != null) controller.cycleDurationWeeks.value = v;
                    },
                  )),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildContextBanner(String title, String subtitle) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D31),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF2563EB).withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.link, color: Color(0xFF60A5FA), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Color(0xFF93C5FD), fontSize: 11.5, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(color: Colors.white, fontSize: 12.5), maxLines: 2, overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required String description,
    required IconData icon,
    required Color iconColor,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: iconColor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(8)),
                child: Icon(icon, color: iconColor, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white)),
                    const SizedBox(height: 2),
                    Text(description, style: const TextStyle(fontSize: 12, color: Colors.white54)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          const Divider(color: Color(0xFF334155), height: 1),
          const SizedBox(height: 20),
          child,
        ],
      ),
    );
  }

  Widget _buildBottomBar(ProjectAnalysisFlowController controller, bool isEn) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        border: Border(top: BorderSide(color: Color(0xFF1E293B))),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          if (controller.currentStep.value > 0)
            OutlinedButton.icon(
              onPressed: () => controller.prevStep(),
              icon: const Icon(Icons.arrow_back, size: 16),
              label: Text(isEn ? 'Back' : 'Quay lại'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white70,
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            )
          else
            const SizedBox.shrink(),

          if (controller.currentStep.value < 2)
            ElevatedButton.icon(
              onPressed: () => controller.nextStep(),
              icon: const Icon(Icons.arrow_forward, size: 16),
              label: Text(isEn ? 'Continue' : 'Tiếp tục bước sau'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
            )
          else
            ElevatedButton.icon(
              onPressed: controller.isSubmitting.value
                  ? null
                  : () async {
                      final success = await controller.submitAndActivate();
                      if (success) {
                        Get.offAllNamed(AppRoutes.hub);
                      }
                    },
              icon: controller.isSubmitting.value
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.check_circle_outline, size: 18),
              label: Text(
                controller.isSubmitting.value
                    ? (isEn ? 'Activating...' : 'Đang kích hoạt...')
                    : (isEn ? 'Activate Plan & Enter Hub' : 'Kích hoạt Kế hoạch & Vào Hub'),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF10B981),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                textStyle: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
        ],
      ),
    );
  }
}
