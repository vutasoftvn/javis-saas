import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../controllers/project_orchestration_controller.dart';
import 'tabs/project_roadmap_tab.dart';

/// Điểm vào thật của SaaS Project Stage & Agent Orchestration trong sidebar
/// DashboardView (nhóm "Chu kỳ") - StrategyView/TabBar không được app render
/// ở đâu cả nên không dùng được làm điểm vào.
class ProjectRoadmapView extends StatelessWidget {
  const ProjectRoadmapView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }
    if (!Get.isRegistered<ProjectOrchestrationController>()) {
      Get.put(ProjectOrchestrationController());
    }
    return const ProjectRoadmapTab();
  }
}
