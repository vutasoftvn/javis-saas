import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../../../core/widgets/floating_app_bar.dart';
import '../../../dashboard/controllers/dashboard_controller.dart';
import '../../../marketing/controllers/marketing_controller.dart';
import '../../controllers/strategy_controller.dart';
import '../../controllers/project_orchestration_controller.dart';
import '../project_kickoff_view.dart';
import '../project_stage_workspace_view.dart';

/// Điểm vào cho SaaS Project Stage & Agent Orchestration: chọn hoặc tạo một
/// Dự án rồi mở MVP roadmap cho dự án đó (design §"Primary workflow" bước
/// 1-2). Mô tả dự án chính là brief mà AI dùng kết hợp Foundation (vision/
/// mission/core values) để thiết kế MVP roadmap và OKRs/12WY - xem
/// ProjectOrchestrationService.generate_roadmap / RoutingService.plan_stage.
///
/// Điều hướng theo kiểu master-detail NGAY TRONG tab này (không push route
/// mới) để giữ nguyên sidebar/appbar chung của DashboardView, thay vì
/// Get.to() vốn thay thế toàn màn hình.
class ProjectRoadmapTab extends StatefulWidget {
  const ProjectRoadmapTab({super.key});

  @override
  State<ProjectRoadmapTab> createState() => _ProjectRoadmapTabState();
}

class _ProjectRoadmapTabState extends State<ProjectRoadmapTab> {
  StrategyController get controller => Get.find<StrategyController>();
  ProjectOrchestrationController get orchestrationController => Get.find<ProjectOrchestrationController>();

  String? _selectedProjectId;
  String? _selectedStageId;

  @override
  void initState() {
    super.initState();
    controller.loadProjects();
  }

  @override
  Widget build(BuildContext context) {
    if (_selectedProjectId != null && _selectedStageId != null) {
      return ProjectStageWorkspaceView(
        key: ValueKey('${_selectedProjectId}_$_selectedStageId'),
        projectId: _selectedProjectId!,
        stageId: _selectedStageId!,
        onBack: () => setState(() => _selectedStageId = null),
      );
    }
    if (_selectedProjectId != null) {
      return ProjectKickoffView(
        key: ValueKey(_selectedProjectId),
        projectId: _selectedProjectId!,
        onBack: () => setState(() {
          _selectedProjectId = null;
          _selectedStageId = null;
        }),
        onOpenStageWorkspace: (stageId) => setState(() => _selectedStageId = stageId),
      );
    }
    return _buildProjectList();
  }

  Widget _buildProjectList() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CosaFloatingAppBar(
            title: 'Dự án & Lộ trình MVP',
            subtitle: 'Chọn hoặc tạo một dự án để lập lộ trình phát triển MVP và OKRs/12 tuần.',
            icon: Icons.rocket_launch_outlined,
            actions: [
              TextButton.icon(
                onPressed: () => Get.find<DashboardController>().changePage(30, 6),
                icon: const Icon(Icons.tune_rounded, size: 16, color: AppTheme.textMutedDark),
                label: const Text('Quản trị Template', style: TextStyle(color: AppTheme.textMutedDark)),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => _showCreateProjectDialog(context),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Dự án mới'),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.projects.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }
              if (controller.projects.isEmpty) {
                return Center(
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 40),
                    padding: const EdgeInsets.all(32),
                    constraints: const BoxConstraints(maxWidth: 520),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.borderDark),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.rocket_launch_rounded, size: 36, color: AppTheme.primary),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Chưa có Dự án nào',
                          style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Tạo dự án mới với ngày bắt đầu (Thứ Hai) và kết thúc để AI tự động thiết kế lộ trình MVP, phân bổ OKRs và chu kỳ thực thi 12 tuần.',
                          style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.4),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                        ElevatedButton.icon(
                          onPressed: () => _showCreateProjectDialog(context),
                          icon: const Icon(Icons.add_rounded, size: 16),
                          label: const Text('Tạo Dự án mới'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            foregroundColor: AppTheme.backgroundDarker,
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }
              return LayoutBuilder(
                builder: (context, constraints) {
                  final crossAxisCount = constraints.maxWidth > 1300
                      ? 4
                      : (constraints.maxWidth > 900
                          ? 3
                          : (constraints.maxWidth > 600 ? 2 : 1));
                  final childAspectRatio = constraints.maxWidth > 1300
                      ? 2.1
                      : (constraints.maxWidth > 900
                          ? 2.2
                          : (constraints.maxWidth > 600 ? 2.3 : 2.8));
                  return GridView.builder(
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: crossAxisCount,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: childAspectRatio,
                    ),
                    itemCount: controller.projects.length,
                    itemBuilder: (context, index) {
                      final project = controller.projects[index] as Map<String, dynamic>;
                      return _projectCard(project);
                    },
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _projectCard(Map<String, dynamic> project) {
    final projectId = project['id']?.toString() ?? '';
    final description = project['description']?.toString();
    final phase = project['phase']?.toString();
    final startDateStr = project['start_date']?.toString();
    final endDateStr = project['end_date']?.toString();

    String? dateBadge;
    if (startDateStr != null && startDateStr.isNotEmpty) {
      try {
        final startDt = DateTime.parse(startDateStr);
        final startFmt = '${startDt.day.toString().padLeft(2, '0')}/${startDt.month.toString().padLeft(2, '0')}';
        if (endDateStr != null && endDateStr.isNotEmpty) {
          final endDt = DateTime.parse(endDateStr);
          final endFmt = '${endDt.day.toString().padLeft(2, '0')}/${endDt.month.toString().padLeft(2, '0')}/${endDt.year}';
          final weeks = ((endDt.difference(startDt).inDays + 1) / 7).ceil();
          dateBadge = '$startFmt – $endFmt ($weeks tuần)';
        } else {
          dateBadge = 'Từ $startFmt/${startDt.year}';
        }
      } catch (_) {}
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: projectId.isEmpty ? null : () => setState(() => _selectedProjectId = projectId),
        borderRadius: BorderRadius.circular(10),
        hoverColor: AppTheme.primary.withValues(alpha: 0.04),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                project['title']?.toString() ?? '',
                style: const TextStyle(
                  color: AppTheme.textDark,
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                  height: 1.25,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (description != null && description.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(
                    color: AppTheme.textMutedDark,
                    fontSize: 11.5,
                    height: 1.3,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              const Spacer(),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  if (phase != null && phase.isNotEmpty)
                    Flexible(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
                        ),
                        child: Text(
                          phase,
                          style: const TextStyle(
                            color: AppTheme.primary,
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                  else if (dateBadge != null)
                    Flexible(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.calendar_today_outlined, size: 10, color: AppTheme.textMutedDark),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(
                                dateBadge,
                                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 10.5),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    const SizedBox.shrink(),
                  const Spacer(),
                  // Open Marketing OS & Flow button
                  Tooltip(
                    message: 'Mở Marketing & Lead Gen',
                    child: SizedBox(
                      width: 32,
                      height: 32,
                      child: IconButton(
                        onPressed: projectId.isEmpty
                            ? null
                            : () {
                                if (Get.isRegistered<MarketingController>()) {
                                  Get.find<MarketingController>().selectProject(projectId);
                                }
                                Get.find<DashboardController>().changePage(17, 0);
                              },
                        icon: const Icon(Icons.campaign_outlined, size: 16),
                        padding: EdgeInsets.zero,
                        color: AppTheme.primaryLight,
                        hoverColor: AppTheme.primary.withValues(alpha: 0.15),
                        style: IconButton.styleFrom(
                          side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.3)),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  // View icon button
                  Tooltip(
                    message: 'Xem Lộ trình MVP',
                    child: SizedBox(
                      width: 32,
                      height: 32,
                      child: IconButton(
                        onPressed: projectId.isEmpty ? null : () => setState(() => _selectedProjectId = projectId),
                        icon: const Icon(Icons.remove_red_eye_outlined, size: 16),
                        padding: EdgeInsets.zero,
                        color: AppTheme.textMutedDark,
                        hoverColor: AppTheme.primary.withValues(alpha: 0.15),
                        style: IconButton.styleFrom(
                          side: BorderSide(color: AppTheme.borderDark),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  // AI auto-generate icon button
                  Obx(() {
                    final isGenerating = orchestrationController.isGeneratingRoadmap.value &&
                        orchestrationController.activeProjectId.value == projectId;
                    return Tooltip(
                      message: 'AI tạo Lộ trình MVP tự động',
                      child: SizedBox(
                        width: 32,
                        height: 32,
                        child: IconButton(
                          onPressed: (projectId.isEmpty || isGenerating)
                              ? null
                              : () => _aiGenerateAndNavigate(projectId),
                          icon: isGenerating
                              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.auto_awesome_rounded, size: 16),
                          padding: EdgeInsets.zero,
                          color: AppTheme.primary,
                          hoverColor: AppTheme.primary.withValues(alpha: 0.15),
                          style: IconButton.styleFrom(
                            backgroundColor: AppTheme.primary.withValues(alpha: 0.12),
                            side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.4)),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// AI tạo roadmap cho project có sẵn rồi tự điều hướng vào ProjectKickoffView.
  Future<void> _aiGenerateAndNavigate(String projectId) async {
    orchestrationController.activeProjectId.value = projectId;
    setState(() => _selectedProjectId = projectId);
    await orchestrationController.generateRoadmap(projectId);
  }

  void _showCreateProjectDialog(BuildContext context) {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();

    // Default start date: Monday of current week
    final now = DateTime.now();
    DateTime startDate = DateTime(now.year, now.month, now.day).subtract(Duration(days: now.weekday - 1));
    // Default end date: Sunday of week 12 (83 days from Monday)
    DateTime endDate = startDate.add(const Duration(days: 83));

    AppModalDialog.show(
      context: context,
      title: 'Dự án mới',
      subtitle: 'Xác định mục tiêu và thời gian triển khai để AI thiết kế lộ trình MVP & OKRs chính xác',
      icon: Icons.rocket_launch_outlined,
      maxWidth: 580,
      content: StatefulBuilder(
        builder: (context, setModalState) {
          final durationDays = endDate.difference(startDate).inDays + 1;
          final durationWeeks = (durationDays / 7).ceil();

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Tên dự án', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
              const SizedBox(height: 6),
              TextField(
                controller: titleController,
                autofocus: true,
                style: const TextStyle(color: AppTheme.textDark),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: Nền tảng định danh điện tử',
                  hintStyle: const TextStyle(color: AppTheme.textMutedDark),
                  filled: true,
                  fillColor: AppTheme.surfaceDarkLighter,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 14),
              const Text('Mô tả dự án (brief cho AI)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
              const SizedBox(height: 6),
              TextField(
                controller: descriptionController,
                maxLines: 3,
                style: const TextStyle(color: AppTheme.textDark),
                decoration: InputDecoration(
                  hintText: 'Vấn đề đang giải quyết, khách hàng mục tiêu, giá trị cốt lõi...',
                  hintStyle: const TextStyle(color: AppTheme.textMutedDark),
                  filled: true,
                  fillColor: AppTheme.surfaceDarkLighter,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Bắt đầu (Thứ Hai)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5)),
                        const SizedBox(height: 6),
                        InkWell(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: startDate,
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2035),
                            );
                            if (picked != null) {
                              // Align to Monday
                              final pickedMonday = picked.subtract(Duration(days: picked.weekday - 1));
                              setModalState(() {
                                startDate = pickedMonday;
                                if (endDate.isBefore(startDate)) {
                                  endDate = startDate.add(const Duration(days: 83));
                                }
                              });
                            }
                          },
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceDarkLighter,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.borderDark),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.calendar_today_rounded, size: 15, color: AppTheme.primary),
                                const SizedBox(width: 8),
                                Text(
                                  '${startDate.day.toString().padLeft(2, '0')}/${startDate.month.toString().padLeft(2, '0')}/${startDate.year}',
                                  style: const TextStyle(color: AppTheme.textDark, fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Dự kiến kết thúc (Chủ Nhật)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5)),
                        const SizedBox(height: 6),
                        InkWell(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: endDate,
                              firstDate: startDate,
                              lastDate: DateTime(2035),
                            );
                            if (picked != null) {
                              // Align to Sunday of that week
                              final pickedSunday = picked.add(Duration(days: 7 - picked.weekday));
                              setModalState(() {
                                endDate = pickedSunday;
                              });
                            }
                          },
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceDarkLighter,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.borderDark),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.event_available_rounded, size: 15, color: AppTheme.secondaryLight),
                                const SizedBox(width: 8),
                                Text(
                                  '${endDate.day.toString().padLeft(2, '0')}/${endDate.month.toString().padLeft(2, '0')}/${endDate.year}',
                                  style: const TextStyle(color: AppTheme.textDark, fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.timer_outlined, size: 15, color: AppTheme.primary),
                    const SizedBox(width: 8),
                    Text(
                      'Thời gian dự kiến: $durationWeeks tuần ($durationDays ngày)',
                      style: const TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ')),
        ElevatedButton(
          onPressed: () async {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            final description = descriptionController.text.trim();
            Get.back();
            await _createProjectAndAutoDraftRoadmap(
              title,
              description.isEmpty ? null : description,
              startDate: startDate,
              endDate: endDate,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
          child: const Text('Tạo dự án'),
        ),
      ],
    );
  }

  /// Chỉ tự động sinh roadmap ở đúng lúc project vừa được tạo. Mở lại một
  /// project có sẵn (ProjectKickoffView) không bao giờ tự gọi AI - founder
  /// phải bấm "AI đề xuất lại" nếu muốn sinh mới, tránh AI âm thầm ghi đè
  /// bản nháp đã sửa tay.
  Future<void> _createProjectAndAutoDraftRoadmap(
    String title,
    String? description, {
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final projectId = await controller.createProject(
      title: title,
      description: description,
      startDate: startDate,
      endDate: endDate,
    );
    if (projectId == null || projectId.isEmpty) return;
    // Điều hướng ngay vào ProjectKickoffView; AI sẽ sinh roadmap trong nền.
    orchestrationController.activeProjectId.value = projectId;
    setState(() => _selectedProjectId = projectId);
    await orchestrationController.generateRoadmap(projectId);
  }
}
