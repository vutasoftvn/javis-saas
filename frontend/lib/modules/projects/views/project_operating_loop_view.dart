import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/lifecycle/lifecycle_service.dart';
import '../../../core/lifecycle/widgets/lifecycle_settings_section.dart';
import '../../strategy/services/project_service.dart';
import '../controllers/project_operating_loop_controller.dart';
import '../widgets/executive_board_stage_suggestion_dialog.dart';
import 'widgets/okr_section.dart';
import 'widgets/cycle_week_section.dart';
import 'widgets/commitment_task_section.dart';
import 'widgets/evidence_decision_section.dart';

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
                  Tab(key: Key('tab_evidence_decisions'), text: 'Evidence & Decisions'),
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
                      ),
                    ),
                    SingleChildScrollView(
                      child: CommitmentTaskSection(
                        controller: controller,
                        activeCycle: loop.activeCycle,
                        tasks: loop.tasks,
                      ),
                    ),
                    SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          EvidenceDecisionSection(
                            controller: controller,
                            evidence: loop.evidence,
                            decisions: loop.decisions,
                          ),
                          const SizedBox(height: 12),
                          _ProjectLifecycleSection(
                            projectId: loop.project.id,
                            workspaceId: loop.project.workspaceId,
                          ),
                        ],
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

/// Task 13 — bọc `LifecycleSettingsSection` cho Project. Không có màn hình
/// "Project Settings" nào tồn tại trong `frontend/lib/modules/` (đã grep xác
/// nhận, quyết định founder 2026-09-14) nên chèn thành 1 section vào cuối tab
/// "Evidence & Decisions" của `ProjectOperatingLoopView` — route thật/live,
/// không tạo màn hình/route mới.
///
/// `controller.loop.value.project` (`ProjectSummary`) không có
/// `lifecycleStage`/`stageVersion` — response của
/// `GET /operations/projects/:id/operating-loop` không serialize 2 field đó
/// (xem `project-operating-loop.service.ts` `toProject()`). Nên widget này tự
/// gọi `ProjectService().getProjects()` (đã tồn tại, gọi
/// `GET /operations/projects`) rồi lọc theo `id == projectId` để lấy giá trị
/// thật — tái dùng service sẵn có, không thêm endpoint mới. `stageVersion`
/// trước đây bị thiếu ngay ở `toProject()` backend (cột DB `stage_version`
/// NOT NULL nhưng bị bỏ sót khỏi response) — đã bổ sung field này vào
/// `Project` interface + `toProject()` trong `project.service.ts` (và bản sao
/// trong `project-operating-loop.service.ts` để đồng bộ type) như một phần
/// của Task 13, vì đây chỉ là thêm field vào response serialize sẵn có,
/// không phải endpoint/migration mới.
class _ProjectLifecycleSection extends StatefulWidget {
  const _ProjectLifecycleSection({
    required this.projectId,
    required this.workspaceId,
  });

  final String projectId;
  final String workspaceId;

  @override
  State<_ProjectLifecycleSection> createState() => _ProjectLifecycleSectionState();
}

class _ProjectLifecycleSectionState extends State<_ProjectLifecycleSection> {
  final _projectService = ProjectService();
  bool _isLoading = true;
  String? _errorMessage;
  String? _currentStage;
  int? _currentStageVersion;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    final result = await _projectService.getProjects();
    if (result.isFailure) {
      setState(() {
        _errorMessage = result.errorMessage;
        _isLoading = false;
      });
      return;
    }
    Map<String, dynamic>? match;
    for (final item in result.items) {
      if (item['id']?.toString() == widget.projectId) {
        match = item;
        break;
      }
    }
    setState(() {
      _currentStage = match?['lifecycleStage']?.toString();
      final rawVersion = match?['stageVersion'];
      _currentStageVersion =
          rawVersion is int ? rawVersion : int.tryParse(rawVersion?.toString() ?? '');
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_errorMessage != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_errorMessage!),
              const SizedBox(height: 8),
              ElevatedButton(onPressed: _load, child: const Text('Thử lại')),
            ],
          ),
        ),
      );
    }
    if (_currentStage == null || _currentStageVersion == null) {
      // Không tìm thấy project trong danh sách hoặc backend thiếu field —
      // không render với giá trị giả.
      return const SizedBox.shrink();
    }
    return LifecycleSettingsSection(
      entityType: LifecycleEntityType.project,
      entityId: widget.projectId,
      currentStage: _currentStage!,
      currentStageVersion: _currentStageVersion!,
      onTransitioned: (newStage) => showExecutiveBoardStageSuggestionDialog(
        context,
        projectId: widget.projectId,
        workspaceId: widget.workspaceId,
      ),
    );
  }
}
