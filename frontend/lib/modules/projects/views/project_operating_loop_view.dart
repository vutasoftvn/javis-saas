import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/project_operating_loop_controller.dart';
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
                      child: EvidenceDecisionSection(
                        controller: controller,
                        evidence: loop.evidence,
                        decisions: loop.decisions,
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
