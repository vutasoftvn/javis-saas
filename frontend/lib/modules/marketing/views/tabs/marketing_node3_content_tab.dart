import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';
import 'content/marketing_campaigns_subtab.dart';
import 'content/marketing_skills_subtab.dart';
import 'content/marketing_loops_subtab.dart';

/// Node 3: AI Thực thi & Chiến dịch (Campaigns, Loops, Skill Registry)
class MarketingNode3ContentTab extends GetView<MarketingController> {
  const MarketingNode3ContentTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MarketingSubTabBar(
            current: controller.contentSubTab.value,
            items: const [
              {'key': 'campaigns', 'label': 'Chiến dịch & Nội dung', 'icon': Icons.campaign_rounded},
              {'key': 'skills', 'label': 'Kho kỹ năng AI (Skill Registry)', 'icon': Icons.auto_awesome_rounded},
              {'key': 'loops', 'label': 'Vòng lặp tăng trưởng', 'icon': Icons.sync_rounded},
            ],
            onSelect: (k) => controller.contentSubTab.value = k,
          ),
          const SizedBox(height: 10),
          Expanded(
            child: _buildSubTabContent(context, controller.contentSubTab.value),
          ),
        ],
      );
    });
  }

  Widget _buildSubTabContent(BuildContext context, String currentTab) {
    switch (currentTab) {
      case 'skills':
        return MarketingSkillsSubtab(controller: controller);
      case 'loops':
        return MarketingLoopsSubtab(controller: controller);
      case 'campaigns':
      default:
        return MarketingCampaignsSubtab(controller: controller);
    }
  }
}
