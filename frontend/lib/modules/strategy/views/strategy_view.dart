import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import 'tabs/foundation_tab.dart';
import 'tabs/okrs_tab.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class StrategyView extends GetView<StrategyController> {
  const StrategyView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }

    return DefaultTabController(
      length: 2,
      child: Container(
        color: Colors.transparent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. Top Floating AppBar Card
            const JavisFloatingAppBar(
              title: 'Chu kỳ & Chiến lược OKRs',
              subtitle: 'Điều chỉnh việc thực thi của nhóm với chu kỳ mục tiêu và nền tảng của công ty.',
            ),

            // 2. Separate Tab Navigation Bar (Ultra-Compact Pill, Tight Width, Centered)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Center(
                child: IntrinsicWidth(
                  child: Container(
                    height: 38,
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(color: AppTheme.borderDark),
                    ),
                    child: TabBar(
                      isScrollable: true,
                      tabAlignment: TabAlignment.center,
                      indicatorSize: TabBarIndicatorSize.tab,
                      indicator: BoxDecoration(
                        color: AppTheme.primary,
                        borderRadius: BorderRadius.circular(100),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.primary.withValues(alpha: 0.4),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      labelColor: const Color(0xFF04070E),
                      unselectedLabelColor: AppTheme.textMutedDark,
                      labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      unselectedLabelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.normal),
                      dividerColor: Colors.transparent,
                      padding: EdgeInsets.zero,
                      labelPadding: const EdgeInsets.symmetric(horizontal: 16),
                      tabs: const [
                        Tab(height: 32, child: Center(child: Text('Chu kỳ & OKRs'))),
                        Tab(height: 32, child: Center(child: Text('Nền tảng Doanh nghiệp'))),
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // 3. Tab Views Content Body
            const Expanded(
              child: TabBarView(
                children: [
                  OkrsTab(),
                  FoundationTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

