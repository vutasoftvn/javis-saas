import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../controllers/approvals_controller.dart';

class ApprovalHeaderBar extends StatelessWidget {
  final ApprovalsController controller;

  const ApprovalHeaderBar({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        border: Border(bottom: BorderSide(color: Color(0xFF1E293B), width: 1.5)),
      ),
      child: Row(
        children: [
          // Title & Subtitle
          const Icon(Icons.verified_user_rounded, color: Colors.blueAccent, size: 28),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Human Approval Inbox',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                L10nKey.approvalsSubtitle.tr,
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
              ),
            ],
          ),
          const Spacer(),

          // Tab Bar Switcher
          Container(
            width: 320,
            height: 38,
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: TabBar(
              controller: controller.tabController,
              indicatorSize: TabBarIndicatorSize.tab,
              dividerColor: Colors.transparent,
              padding: EdgeInsets.zero,
              labelPadding: EdgeInsets.zero,
              indicator: BoxDecoration(
                color: Colors.blueAccent,
                borderRadius: BorderRadius.circular(7),
              ),
              labelColor: Colors.white,
              unselectedLabelColor: Colors.grey,
              labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5),
              tabs: [
                Obx(() => Tab(
                      height: 32,
                      text: '${L10nKey.approvalsTabPending.tr} (${controller.pendingApprovals.length})',
                    )),
                Tab(height: 32, text: L10nKey.approvalsTabHistory.tr),
              ],
            ),
          ),

          const SizedBox(width: 14),

          // Refresh Button
          IconButton(
            tooltip: L10nKey.commonRefresh.tr,
            onPressed: () => controller.loadApprovals(),
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
