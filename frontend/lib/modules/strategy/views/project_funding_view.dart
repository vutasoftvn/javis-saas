import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../controllers/foundation_controller.dart';
import 'tabs/project_funding_tab.dart';

/// Điểm vào của Module Nguồn lực & Chính sách (Policy / Funding Intelligence & Seed Catalog)
/// trong sidebar DashboardView (nhóm "Chu kỳ").
class ProjectFundingView extends StatelessWidget {
  final String? projectId;

  const ProjectFundingView({super.key, this.projectId});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }
    if (!Get.isRegistered<FoundationController>()) {
      Get.put(FoundationController());
    }
    return ProjectFundingTab(projectId: projectId);
  }
}
