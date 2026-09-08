import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/contracts/enums.generated.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/ui/layout_breakpoints.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../controllers/project_kickoff_controller.dart';
import '../domain/review_schedule.dart';

import '../widgets/workspace_strategy_settings_sheet.dart';

class ProjectKickoffView extends StatefulWidget {
  final String projectId;
  final VoidCallback onBack;
  final void Function(String projectId) onActivated;
  final VoidCallback onOpenAdvancedRoadmap;

  const ProjectKickoffView({
    super.key,
    required this.projectId,
    required this.onBack,
    required this.onActivated,
    required this.onOpenAdvancedRoadmap,
  });

  @override
  State<ProjectKickoffView> createState() => _ProjectKickoffViewState();
}

class _ProjectKickoffViewState extends State<ProjectKickoffView> {
  late final ProjectKickoffController controller;
  late final String _tag;
  bool _isLocalController = false;

  // Bước hiển thị ở frame trước — dùng để suy ra chiều chuyển cảnh của
  // `AnimatedSwitcher` (tiến: trượt từ phải; lùi: trượt từ trái).
  int _prevStep = 0;

  // Tag theo `projectId`: hai `ProjectKickoffView` cho hai project khác nhau
  // (vd. một cái còn sống dưới Navigator stack khi cái kia mở `/projects/new`)
  // KHÔNG được share chung 1 controller — nếu không, dispose() của bên này sẽ
  // huỷ luôn TextEditingController mà bên kia đang render, gây crash "used
  // after disposed".
  @override
  void initState() {
    super.initState();
    _tag = widget.projectId;
    if (Get.isRegistered<ProjectKickoffController>(tag: _tag)) {
      controller = Get.find<ProjectKickoffController>(tag: _tag);
    } else {
      controller = Get.put(ProjectKickoffController(), tag: _tag);
      _isLocalController = true;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && widget.projectId.isNotEmpty) {
        controller.load(widget.projectId);
      }
    });
  }

  @override
  void didUpdateWidget(covariant ProjectKickoffView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.projectId != widget.projectId &&
        widget.projectId.isNotEmpty) {
      controller.load(widget.projectId);
    }
  }

  @override
  void dispose() {
    if (_isLocalController &&
        Get.isRegistered<ProjectKickoffController>(tag: _tag)) {
      Get.delete<ProjectKickoffController>(tag: _tag);
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
            CosaFloatingAppBar(
              title: L10nKey.projectKickoffTitle.tr,
              subtitle: L10nKey.projectKickoffSubtitle.tr,
              icon: Icons.flag_circle_outlined,
              actions: [
                IconButton(
                  key: const ValueKey('project_kickoff_strategy_settings_button'),
                  icon: const Icon(
                    Icons.settings_suggest_outlined,
                    size: 20,
                    color: AppTheme.primary,
                  ),
                  tooltip: L10nKey.projectKickoffSettingsTooltip.tr,
                  onPressed: () => WorkspaceStrategySettingsSheet.show(context),
                ),
                const SizedBox(width: 4),
                TextButton.icon(
                  onPressed: widget.onOpenAdvancedRoadmap,
                  icon: const Icon(
                    Icons.alt_route_rounded,
                    size: 16,
                    color: AppTheme.primary,
                  ),
                  label: Text(
                    L10nKey.projectKickoffAdvancedRoadmap.tr,
                    style: const TextStyle(color: AppTheme.primary),
                  ),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: widget.onBack,
                  icon: const Icon(
                    Icons.arrow_back_rounded,
                    size: 16,
                    color: AppTheme.textMutedDark,
                  ),
                  label: Text(
                    L10nKey.projectKickoffBack.tr,
                    style: const TextStyle(color: AppTheme.textMutedDark),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),
            Expanded(
              // `LayoutBuilder` PHẢI ở ngoài `Obx`: builder của nó chạy ở pha
              // layout, ngoài phạm vi theo dõi đồng bộ của `Obx`. Nếu bọc nội
              // dung bước bên trong `LayoutBuilder`, `Obx` không "nhìn thấy" các
              // observable đọc trong đó (evidenceLevel, currentStep...) nên bấm
              // radio / "Tiếp tục" cập nhật state mà không rebuild.
              child: LayoutBuilder(
                builder: (context, constraints) {
                  // Bề rộng nội dung theo 3 bậc layout (layout_breakpoints là
                  // nguồn sự thật duy nhất): desktop 4/12, tablet 6/12, mobile
                  // full trừ 16px padding mỗi bên. Nội dung luôn căn giữa.
                  final double contentWidth = switch (layoutForWidth(
                    constraints.maxWidth,
                  )) {
                    AppLayout.expanded => constraints.maxWidth * 4 / 12,
                    AppLayout.medium => constraints.maxWidth * 6 / 12,
                    AppLayout.compact => constraints.maxWidth - 32,
                  };
                  return Obx(() {
                    if (controller.isLoading.value) {
                      return const Center(child: CircularProgressIndicator());
                    }

                    final error = controller.errorMessage.value;

                    return SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Center(
                        child: SizedBox(
                          width: contentWidth,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              if (error != null)
                                Container(
                                  margin: const EdgeInsets.only(bottom: 16),
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: AppTheme.error.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                      color: AppTheme.error.withValues(
                                        alpha: 0.4,
                                      ),
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(
                                        Icons.error_outline_rounded,
                                        color: AppTheme.error,
                                        size: 18,
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          error,
                                          style: const TextStyle(
                                            color: AppTheme.error,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              _buildStepProgress(),
                              const SizedBox(height: 16),
                              _buildAnimatedStepContent(),
                            ],
                          ),
                        ),
                      ),
                    );
                  });
                },
              ),
            ),
          ],
        ),
      );
  }

  Widget _buildStepProgress() {
    final steps = [
      L10nKey.projectKickoffStepTab1.tr,
      L10nKey.projectKickoffStepTab2.tr,
      L10nKey.projectKickoffStepTab3.tr,
    ];
    final current = controller.currentStep.value;
    // Thanh "track" của tab: nền tối nhất để pill active (nền primary) nổi bật.
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppTheme.backgroundDarker,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          for (int i = 0; i < steps.length; i++)
            Expanded(
              child: _stepTab(
                index: i,
                label: steps[i],
                isActive: current == i,
                isDone: current > i,
              ),
            ),
        ],
      ),
    );
  }

  // Một tab bước. 3 trạng thái rõ ràng:
  // - active  : pill nền primary, chữ đậm màu nền tối, có đổ bóng.
  // - done    : nền trong suốt, icon check xanh, chữ trắng — bấm để quay lại.
  // - upcoming: nền trong suốt, badge số mờ, chữ mờ — không bấm được.
  Widget _stepTab({
    required int index,
    required String label,
    required bool isActive,
    required bool isDone,
  }) {
    final canTap = isDone && !isActive;
    final Color fg = isActive
        ? AppTheme.backgroundDarker
        : (isDone ? AppTheme.textDark : AppTheme.textMutedDark);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      decoration: BoxDecoration(
        color: isActive ? AppTheme.primary : Colors.transparent,
        borderRadius: BorderRadius.circular(9),
        boxShadow: isActive
            ? [
                BoxShadow(
                  color: AppTheme.primary.withValues(alpha: 0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: canTap ? () => _goToStep(index) : null,
          borderRadius: BorderRadius.circular(9),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (isDone && !isActive)
                  const Icon(
                    Icons.check_circle_rounded,
                    size: 18,
                    color: AppTheme.success,
                  )
                else
                  Container(
                    width: 20,
                    height: 20,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isActive
                          ? Colors.white.withValues(alpha: 0.25)
                          : AppTheme.surfaceDarkLighter,
                    ),
                    child: Text(
                      '${index + 1}',
                      style: TextStyle(
                        color: fg,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    label,
                    textAlign: TextAlign.center,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: fg,
                      fontSize: 13,
                      fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStepContent() {
    final step = controller.currentStep.value;
    if (step == 0) return _buildStep1Understand();
    if (step == 1) return _buildStep2Stage();
    return _buildStep3FirstWeek();
  }

  // Chuyển cảnh mượt giữa các bước: fade + trượt ngang nhẹ theo chiều di
  // chuyển. Phải được gọi trong closure của `Obx` để `currentStep.value`
  // được theo dõi.
  Widget _buildAnimatedStepContent() {
    final step = controller.currentStep.value;
    final forward = step >= _prevStep;
    _prevStep = step;
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 260),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      layoutBuilder: (currentChild, previousChildren) => Stack(
        alignment: Alignment.topCenter,
        children: [...previousChildren, ?currentChild],
      ),
      transitionBuilder: (child, animation) {
        final slide = Tween<Offset>(
          begin: Offset(forward ? 0.06 : -0.06, 0),
          end: Offset.zero,
        ).animate(animation);
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(position: slide, child: child),
        );
      },
      child: KeyedSubtree(key: ValueKey<int>(step), child: _buildStepContent()),
    );
  }

  // Tab điều hướng: chỉ cho quay lại bước đã hoàn thành (giống nút "Quay
  // lại" — lưu nháp không chặn rồi đổi bước). Tiến tới vẫn phải qua nút
  // "Tiếp tục" của từng bước để chạy validate trước khi cho đi tiếp.
  void _goToStep(int index) {
    if (index >= controller.currentStep.value) return;
    controller.saveCurrentStep();
    controller.currentStep.value = index;
  }

  // ── Step 1: Hiểu dự án ──
  Widget _buildStep1Understand() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            L10nKey.projectKickoffStep1Title.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 17,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),

          // Question 1
          Text(
            L10nKey.projectKickoffTargetCustomerLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: controller.targetCustomerCtrl,
            style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
            decoration: InputDecoration(
              hintText: L10nKey.projectKickoffTargetCustomerHint.tr,
              hintStyle: const TextStyle(
                color: AppTheme.textMutedDark,
                fontSize: 13,
              ),
              filled: true,
              fillColor: AppTheme.backgroundDarker,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: AppTheme.borderDark),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 12,
              ),
            ),
          ),
          const SizedBox(height: 18),

          // Question 2
          Text(
            L10nKey.projectKickoffProblemStatementLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: controller.problemStatementCtrl,
            maxLines: 3,
            style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
            decoration: InputDecoration(
              hintText: L10nKey.projectKickoffProblemStatementHint.tr,
              hintStyle: const TextStyle(
                color: AppTheme.textMutedDark,
                fontSize: 13,
              ),
              filled: true,
              fillColor: AppTheme.backgroundDarker,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: AppTheme.borderDark),
              ),
              contentPadding: const EdgeInsets.all(12),
            ),
          ),
          const SizedBox(height: 18),

          // Question 3
          Text(
            L10nKey.projectKickoffEvidenceLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
          RadioGroup<KickoffEvidenceLevel>(
            groupValue: controller.evidenceLevel.value,
            onChanged: (value) {
              if (value != null) controller.selectEvidence(value);
            },
            child: Column(
              children: [
                for (final level in KickoffEvidenceLevel.values)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Material(
                      color: controller.evidenceLevel.value == level
                          ? AppTheme.primary.withValues(alpha: 0.12)
                          : AppTheme.backgroundDarker,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(
                          color: controller.evidenceLevel.value == level
                              ? AppTheme.primary
                              : AppTheme.borderDark,
                        ),
                      ),
                      child: RadioListTile<KickoffEvidenceLevel>(
                        value: level,
                        activeColor: AppTheme.primary,
                        title: Text(
                          level.localizedLabel,
                          style: const TextStyle(
                            color: AppTheme.textDark,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Actions
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton.icon(
                onPressed:
                    controller.targetCustomerCtrl.text.trim().isEmpty ||
                        controller.problemStatementCtrl.text.trim().isEmpty ||
                        controller.evidenceLevel.value == null ||
                        controller.isSaving.value
                    ? null
                    : () async {
                        final ok = await controller.saveCurrentStep();
                        if (ok) controller.currentStep.value = 1;
                      },
                icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: AppTheme.backgroundDarker,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                ),
                label: Text(
                  controller.isSaving.value
                      ? L10nKey.projectKickoffSaving.tr
                      : L10nKey.projectKickoffContinue.tr,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ── Step 2: Chọn vòng đầu ──
  Widget _buildStep2Stage() {
    final evidence = controller.evidenceLevel.value;
    final recommended = KickoffStagePolicy.recommend(evidence);
    final isP1Recommended =
        recommended == ProjectLifecycleStage.p1ProblemValidation;

    final proposalText = isP1Recommended
        ? L10nKey.projectKickoffProposalP1.tr
        : L10nKey.projectKickoffProposalP0.tr;
    final proposalGoal = isP1Recommended
        ? L10nKey.projectKickoffGoalP1.tr
        : L10nKey.projectKickoffGoalP0.tr;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            L10nKey.projectKickoffStep2Title.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 17,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),

          // Proposal Banner
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppTheme.primary.withValues(alpha: 0.4),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.auto_awesome_rounded,
                  color: AppTheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        proposalText,
                        style: const TextStyle(
                          color: AppTheme.primary,
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        proposalGoal,
                        style: const TextStyle(
                          color: AppTheme.textDark,
                          fontSize: 13,
                          height: 1.3,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Stage Options
          Text(
            L10nKey.projectKickoffSelectStageLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 10),

          Row(
            children: [
              Expanded(
                child: _stageSelectionCard(
                  stage: ProjectLifecycleStage.p0Discovery,
                  title: L10nKey.projectKickoffStageP0Title.tr,
                  subtitle: L10nKey.projectKickoffStageP0Subtitle.tr,
                  isSelected:
                      controller.selectedStage.value ==
                      ProjectLifecycleStage.p0Discovery,
                  isEnabled: true,
                  onTap: () =>
                      controller.selectStage(ProjectLifecycleStage.p0Discovery),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _stageSelectionCard(
                  stage: ProjectLifecycleStage.p1ProblemValidation,
                  title: L10nKey.projectKickoffStageP1Title.tr,
                  subtitle: L10nKey.projectKickoffStageP1Subtitle.tr,
                  isSelected:
                      controller.selectedStage.value ==
                      ProjectLifecycleStage.p1ProblemValidation,
                  isEnabled: controller.isP1Allowed,
                  onTap: controller.isP1Allowed
                      ? () => controller.selectStage(
                          ProjectLifecycleStage.p1ProblemValidation,
                        )
                      : null,
                ),
              ),
            ],
          ),

          if (!controller.isP1Allowed &&
              controller.selectedStage.value ==
                  ProjectLifecycleStage.p1ProblemValidation)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                L10nKey.projectKickoffP1Warning.tr,
                style: const TextStyle(color: AppTheme.warning, fontSize: 13),
              ),
            ),

          const SizedBox(height: 20),

          // Duration Chips
          Text(
            L10nKey.projectKickoffCycleDurationLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),

          Wrap(spacing: 8, children: _buildDurationChips()),

          const SizedBox(height: 20),
          Text(
            L10nKey.projectKickoffCycleStartDateLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
          _roundStartPicker(),

          const SizedBox(height: 24),

          // Actions
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            spacing: 12,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: () {
                  controller.saveCurrentStep();
                  controller.currentStep.value = 0;
                },
                child: Text(L10nKey.projectKickoffBack.tr),
              ),
              ElevatedButton.icon(
                onPressed: controller.isSaving.value
                    ? null
                    : () async {
                        final ok = await controller.saveCurrentStep();
                        if (ok) {
                          controller.currentStep.value = 2;
                          controller.requestKickoffSuggestion(overwrite: false);
                        }
                      },
                icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: AppTheme.backgroundDarker,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                ),
                label: Text(
                  controller.isSaving.value
                      ? L10nKey.projectKickoffSaving.tr
                      : L10nKey.projectKickoffContinue.tr,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  List<Widget> _buildDurationChips() {
    final stage = controller.selectedStage.value;
    final options = stage == ProjectLifecycleStage.p0Discovery
        ? [1, 2]
        : [2, 3, 4];
    return options.map((weeks) {
      final isSelected = controller.stageDurationWeeks.value == weeks;
      return ChoiceChip(
        label: Text(
          L10nKey.projectKickoffWeeksCount.trParams({'weeks': '$weeks'}),
        ),
        selected: isSelected,
        selectedColor: AppTheme.primary,
        backgroundColor: AppTheme.backgroundDarker,
        labelStyle: TextStyle(
          color: isSelected ? AppTheme.backgroundDarker : AppTheme.textDark,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
        onSelected: (_) => controller.selectDuration(weeks),
      );
    }).toList();
  }

  Widget _stageSelectionCard({
    required ProjectLifecycleStage stage,
    required String title,
    required String subtitle,
    required bool isSelected,
    required bool isEnabled,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: isEnabled ? onTap : null,
      borderRadius: BorderRadius.circular(10),
      child: Opacity(
        opacity: isEnabled ? 1.0 : 0.5,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected
                ? AppTheme.primary.withValues(alpha: 0.15)
                : AppTheme.backgroundDarker,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isSelected ? AppTheme.primary : AppTheme.borderDark,
              width: isSelected ? 1.5 : 1.0,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: isSelected ? AppTheme.primary : AppTheme.textDark,
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: const TextStyle(
                  color: AppTheme.textMutedDark,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _step3ContextLine() {
    final weeks = controller.stageDurationWeeks.value;
    final stageLabel =
        controller.selectedStage.value ==
            ProjectLifecycleStage.p1ProblemValidation
        ? L10nKey.projectKickoffStageP1Title.tr
        : L10nKey.projectKickoffStageP0Title.tr;
    return L10nKey.projectKickoffStep3Context.trParams({
      'stage': stageLabel,
      'weeks': '$weeks',
    });
  }

  // ── Step 3: Chốt việc tuần đầu ──
  Widget _buildStep3FirstWeek() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  L10nKey.projectKickoffStep3Title.tr,
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (controller.aiSuggestionLoading.value)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                IconButton(
                  icon: const Icon(Icons.auto_awesome, size: 20),
                  color: AppTheme.primary,
                  tooltip: L10nKey.projectKickoffRegenerateAiTooltip.tr,
                  onPressed: () =>
                      controller.requestKickoffSuggestion(overwrite: true),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                ),
            ],
          ),
          const SizedBox(height: 16),

          Text(
            _step3ContextLine(),
            style: const TextStyle(
              color: AppTheme.textMutedDark,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),

          // Outcome
          Text(
            L10nKey.projectKickoffFirstWeekOutcomeLabel.tr,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            L10nKey.projectKickoffFirstWeekOutcomeHint.tr,
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: controller.firstWeekOutcomeCtrl,
            style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
            decoration: InputDecoration(
              hintText: L10nKey.projectKickoffFirstWeekOutcomeInputHint.tr,
              hintStyle: const TextStyle(
                color: AppTheme.textMutedDark,
                fontSize: 13,
              ),
              filled: true,
              fillColor: AppTheme.backgroundDarker,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: AppTheme.borderDark),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 12,
              ),
            ),
          ),
          const SizedBox(height: 18),

          // Actions List (1 to 3 items)
          Row(
            children: [
              Expanded(
                child: Text(
                  L10nKey.projectKickoffFirstWeekActionsLabel.tr,
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                L10nKey.projectKickoffActionsCount.trParams({
                  'count': '${controller.firstWeekActions.length}',
                }),
                style: const TextStyle(
                  color: AppTheme.textMutedDark,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          for (int i = 0; i < controller.firstWeekActions.length; i++)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.backgroundDarker,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: Row(
                children: [
                  Container(
                    width: 22,
                    height: 22,
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                    ),
                    child: Center(
                      child: Text(
                        '${i + 1}',
                        style: const TextStyle(
                          color: AppTheme.primary,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      controller.firstWeekActions[i].title,
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.close_rounded,
                      size: 16,
                      color: AppTheme.textMutedDark,
                    ),
                    onPressed: controller.isSaving.value
                        ? null
                        : () => controller.removeAction(i),
                    tooltip: L10nKey.projectKickoffDeleteActionTooltip.tr,
                  ),
                ],
              ),
            ),

          if (controller.firstWeekActions.length < 3) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller.newActionCtrl,
                    enabled: !controller.isSaving.value,
                    style: const TextStyle(
                      color: AppTheme.textDark,
                      fontSize: 13,
                    ),
                    decoration: InputDecoration(
                      hintText: L10nKey.projectKickoffNewActionHint.tr,
                      hintStyle: const TextStyle(
                        color: AppTheme.textMutedDark,
                        fontSize: 12,
                      ),
                      filled: true,
                      fillColor: AppTheme.backgroundDarker,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(
                          color: AppTheme.borderDark,
                        ),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                    ),
                    onSubmitted: (val) => controller.addAction(val),
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: controller.isSaving.value
                      ? null
                      : () =>
                            controller.addAction(controller.newActionCtrl.text),
                  icon: const Icon(Icons.add_rounded, size: 16),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.surfaceDarkLighter,
                    foregroundColor: AppTheme.textDark,
                    side: const BorderSide(color: AppTheme.borderDark),
                  ),
                  label: Text(L10nKey.projectKickoffAddActionButton.tr),
                ),
              ],
            ),
          ],

          const SizedBox(height: 20),

          // Cadence info
          _buildWeeklyReviewCadence(),

          const SizedBox(height: 24),

          // Actions
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            spacing: 12,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: () {
                  controller.saveCurrentStep();
                  controller.currentStep.value = 1;
                },
                child: Text(L10nKey.projectKickoffBack.tr),
              ),
              ElevatedButton.icon(
                onPressed:
                    !controller.canActivate || controller.isActivating.value
                    ? null
                    : () async {
                        final ok = await controller.activate();
                        if (ok) {
                          widget.onActivated(widget.projectId);
                        }
                      },
                icon: const Icon(Icons.check_circle_outline_rounded, size: 16),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.success,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                ),
                label: Text(
                  controller.isActivating.value
                      ? L10nKey.projectKickoffActivating.tr
                      : L10nKey.projectKickoffConfirmCycle.tr,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Map<int, String> get _weekdayLabels => {
    1: L10nKey.weekdayMonday.tr,
    2: L10nKey.weekdayTuesday.tr,
    3: L10nKey.weekdayWednesday.tr,
    4: L10nKey.weekdayThursday.tr,
    5: L10nKey.weekdayFriday.tr,
    6: L10nKey.weekdaySaturday.tr,
    7: L10nKey.weekdaySunday.tr,
  };

  static const _timeOptions = [
    '09:00',
    '10:00',
    '14:00',
    '15:00',
    '16:00',
    '17:00',
  ];

  // Trước fix, "Ngày review tuần" là 1 dòng Text tĩnh — Founder không có cách
  // nào đổi lịch review dù `weeklyReviewWeekday`/`weeklyReviewTime` đã sẵn
  // trong controller và được gửi lên backend khi activate.
  Widget _buildWeeklyReviewCadence() {
    final currentTime = controller.weeklyReviewTime.value;
    final timeOptions = _timeOptions.contains(currentTime)
        ? _timeOptions
        : ([..._timeOptions, currentTime]..sort());

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderDark),
      ),
      // `Column`: hàng chọn ngày/giờ review + dòng lịch review đã resolve bên
      // dưới. Hàng chọn dùng `Wrap` (thay `Row`) để ở bậc layout hẹp (mobile /
      // tablet 6/12) nhãn và hai dropdown xuống dòng thay vì tràn ngang
      // (RenderFlex overflow).
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 10,
            runSpacing: 6,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.calendar_today_rounded,
                    size: 16,
                    color: AppTheme.primary,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    L10nKey.projectKickoffWeeklyReviewDayLabel.tr,
                    style: const TextStyle(
                      color: AppTheme.textDark,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              DropdownButton<int>(
                value: controller.weeklyReviewWeekday.value,
                dropdownColor: AppTheme.surfaceDark,
                underline: const SizedBox.shrink(),
                style: const TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
                items: _weekdayLabels.entries
                    .map(
                      (e) =>
                          DropdownMenuItem(value: e.key, child: Text(e.value)),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) {
                    controller.updateWeeklyReviewCadence(weekday: value);
                  }
                },
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    '·',
                    style: TextStyle(
                      color: AppTheme.textMutedDark,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(width: 4),
                  DropdownButton<String>(
                    value: currentTime,
                    dropdownColor: AppTheme.surfaceDark,
                    underline: const SizedBox.shrink(),
                    style: const TextStyle(
                      color: AppTheme.textDark,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                    items: timeOptions
                        .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        controller.updateWeeklyReviewCadence(time: value);
                      }
                    },
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          _reviewScheduleLine(),
        ],
      ),
    );
  }

  // Dòng lịch review đã resolve. Là method (không phải `Builder`) để các
  // `controller.*.value` được đọc trong phạm vi theo dõi đồng bộ của `Obx` cha
  // — `Builder.builder` chạy ngoài cửa sổ đó (cùng cơ chế lỗi với regression
  // LayoutBuilder/Obx ghi ở đầu file).
  Widget _reviewScheduleLine() {
    final sched = ReviewSchedule.resolve(
      roundStart: controller.effectiveRoundStart,
      weekday: controller.weeklyReviewWeekday.value,
      time: controller.weeklyReviewTime.value,
      durationWeeks: controller.stageDurationWeeks.value,
    );
    final dd = sched.occurrences
        .map(
          (d) =>
              '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}',
        )
        .join(' & ');
    final hh = controller.weeklyReviewTime.value;
    return Text(
      L10nKey.projectKickoffReviewScheduleText.trParams({
        'date': dd,
        'time': hh,
      }),
      style: const TextStyle(
        color: AppTheme.textMutedDark,
        fontSize: 12,
        height: 1.4,
      ),
    );
  }

  Widget _roundStartPicker() {
    final d = controller.effectiveRoundStart;
    final label =
        '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
    final isDefault = controller.roundStartDate.value == null;
    // `Wrap` thay cho `Row`: ở bậc layout hẹp nhãn "mặc định" xuống dòng thay
    // vì tràn ngang (RenderFlex overflow) — cùng lý do với cadence widget.
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 10,
      runSpacing: 6,
      children: [
        OutlinedButton.icon(
          onPressed: () async {
            final now = DateTime.now();
            final firstDate = DateTime(now.year, now.month, now.day);
            final lastDate = firstDate.add(const Duration(days: 60));
            // Kẹp `initialDate` vào [firstDate, lastDate]: setup RESUME có thể
            // mang `roundStartDate` đã ở quá khứ -> `showDatePicker` assert
            // (`!initialDate.isBefore(firstDate)`) và văng màn đỏ.
            final initialDate = d.isBefore(firstDate)
                ? firstDate
                : (d.isAfter(lastDate) ? lastDate : d);
            final picked = await showDatePicker(
              context: context,
              initialDate: initialDate,
              firstDate: firstDate,
              lastDate: lastDate,
            );
            if (picked != null) controller.setRoundStart(picked);
          },
          icon: const Icon(Icons.event_rounded, size: 16),
          label: Text(label),
        ),
        if (isDefault)
          Text(
            L10nKey.projectKickoffDefaultNextMonday.tr,
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
          ),
      ],
    );
  }
}
