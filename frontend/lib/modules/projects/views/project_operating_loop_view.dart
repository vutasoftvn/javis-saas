import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/lifecycle/lifecycle_service.dart';
import '../../../core/lifecycle/widgets/lifecycle_settings_section.dart';
import '../controllers/project_operating_loop_controller.dart';
import '../widgets/executive_board_stage_suggestion_dialog.dart';
import 'widgets/okr_section.dart';
import 'widgets/cycle_week_section.dart';
import 'widgets/commitment_task_section.dart';

class ProjectOperatingLoopView extends GetView<ProjectOperatingLoopController> {
  final String? projectId;
  const ProjectOperatingLoopView({super.key, this.projectId});

  @override
  ProjectOperatingLoopController get controller {
    if (projectId != null && projectId!.isNotEmpty) {
      if (Get.isRegistered<ProjectOperatingLoopController>(tag: projectId)) {
        return Get.find<ProjectOperatingLoopController>(tag: projectId);
      }
      return Get.put(ProjectOperatingLoopController(projectId: projectId!), tag: projectId);
    }
    return super.controller;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Obx(() {
          final title = controller.loop.value?.project.title ?? 'Project Operating Loop';
          return Text(title);
        }),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Reload Loop',
            onPressed: () => controller.loadLoop(),
          ),
        ],
      ),
      body: Obx(() {
        if (controller.isLoading.value && controller.loop.value == null) {
          return const Center(
            child: CircularProgressIndicator(key: Key('project_loading_indicator')),
          );
        }

        if (controller.errorMessage.value != null && controller.loop.value == null) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 48, color: Colors.red),
                  const SizedBox(height: 16),
                  Text(
                    controller.errorMessage.value!,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => controller.loadLoop(),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          );
        }

        final loop = controller.loop.value;
        if (loop == null) {
          return const Center(child: Text('No project data available'));
        }

        return DefaultTabController(
          length: 4,
          child: Column(
            children: [
              const TabBar(
                isScrollable: true,
                tabs: [
                  Tab(key: Key('tab_okrs'), text: 'OKRs'),
                  Tab(key: Key('tab_cycle_weekly'), text: 'Cycle & Weekly'),
                  Tab(key: Key('tab_tasks'), text: 'Tasks'),
                  Tab(key: Key('tab_lifecycle'), text: 'Lifecycle'),
                ],
              ),
              Expanded(
                child: TabBarView(
                  children: [
                    SingleChildScrollView(
                      child: OkrSection(
                        controller: controller,
                        objectives: loop.objectives,
                      ),
                    ),
                    SingleChildScrollView(
                      child: CycleWeekSection(
                        controller: controller,
                        activeCycle: loop.activeCycle,
                        currentWeek: loop.currentWeek,
                      ),
                    ),
                    SingleChildScrollView(
                      child: CommitmentTaskSection(
                        controller: controller,
                        currentWeek: loop.currentWeek,
                        commitments: loop.commitments,
                        tasks: loop.tasks,
                      ),
                    ),
                    SingleChildScrollView(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: _ProjectLifecycleSection(
                          projectId: loop.project.id,
                          workspaceId: loop.project.workspaceId,
                          lifecycleStage: loop.project.lifecycleStage,
                          stageVersion: loop.project.stageVersion,
                          onTransitioned: () => controller.loadLoop(),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      }),
    );
  }
}

/// Task 13 → Task 4 (2026-09-14 remediation) — trước đây tự gọi
/// `ProjectService().getProjects()` để lấy `lifecycleStage`/`stageVersion` vì
/// `GET .../operating-loop` khi đó chưa serialize 2 field này. Task 3 đã bổ
/// sung 2 field vào `Project` DTO backend, và Task 4 đã thêm chúng vào
/// `ProjectSummary` (Dart) — nên widget này giờ CHỈ đọc trực tiếp từ dữ liệu
/// loop đã tải, không còn round-trip mạng riêng thứ 2. "Evidence & Decisions"
/// tab cũ (field không hề tồn tại ở backend) đã bị xoá hẳn — section này
/// chuyển sang tab "Lifecycle" độc lập, đây là dữ liệu thật, không phải chỗ
/// trống giả làm dữ liệu xác nhận.
class _ProjectLifecycleSection extends StatelessWidget {
  const _ProjectLifecycleSection({
    required this.projectId,
    required this.workspaceId,
    required this.lifecycleStage,
    required this.stageVersion,
    required this.onTransitioned,
  });

  final String projectId;
  final String workspaceId;
  final String lifecycleStage;
  final int stageVersion;
  final Future<void> Function() onTransitioned;

  @override
  Widget build(BuildContext context) {
    if (lifecycleStage.isEmpty) {
      // Backend chưa gửi lifecycleStage — không render với giá trị giả.
      return const SizedBox.shrink();
    }
    return LifecycleSettingsSection(
      entityType: LifecycleEntityType.project,
      entityId: projectId,
      currentStage: lifecycleStage,
      currentStageVersion: stageVersion,
      onTransitioned: (newStage) async {
        // Task 4 — chuyển giai đoạn thành công phải tải lại loop để tab này
        // (và toàn bộ view) phản ánh `stageVersion` mới, không giữ giá trị cũ
        // đã cache trong bộ nhớ controller.
        await onTransitioned();
        if (context.mounted) {
          await showExecutiveBoardStageSuggestionDialog(
            context,
            projectId: projectId,
            workspaceId: workspaceId,
          );
        }
      },
    );
  }
}
