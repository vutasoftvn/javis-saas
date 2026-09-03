import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import 'tabs/strategy_lenses_tab.dart';
import 'tabs/evidence_backbone_tab.dart';
import 'tabs/decision_log_tab.dart';
import 'tabs/stage_gate_audit_tab.dart';
import 'tabs/twelve_wy_loop_tab.dart';
import 'tabs/validation_studio_tab.dart';
import 'tabs/weekly_review_tab.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class StrategyView extends GetView<StrategyController> {
  final int initialTabIndex;
  const StrategyView({super.key, this.initialTabIndex = 0});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }

    return DefaultTabController(
      initialIndex: initialTabIndex,
      length: 7,
      child: Container(
        color: Colors.transparent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. Top Floating AppBar Card
            CosaFloatingAppBar(
              title: 'Không Gian Chiến Lược Toàn Diện (COSA Strategy Engine)',
              subtitle: '6 Trụ cột cốt lõi: Validation Studio, 4 Lăng kính, Trục giả định & bằng chứng, Bộ nhớ quyết định, Stage-Gate và Vòng lặp 12WY.',
              icon: Icons.lightbulb_outline,
            ),

            // 2. Separate Tab Navigation Bar (6 Modern Strategy Tabs)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Center(
                child: IntrinsicWidth(
                  child: Container(
                    height: 42,
                    padding: const EdgeInsets.all(4),
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
                        gradient: const LinearGradient(
                          colors: [Color(0xFF14B8A6), Color(0xFF38BDF8)],
                        ),
                        borderRadius: BorderRadius.circular(100),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF14B8A6).withValues(alpha: 0.35),
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
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.rocket_launch_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('1. Validation Studio'),
                            ],
                          ),
                        ),
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.lens_blur_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('2. Lăng Kính (PESTEL/SWOT/BSC)'),
                            ],
                          ),
                        ),
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.hub_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('3. Trục Giả Định & Bằng Chứng'),
                            ],
                          ),
                        ),
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.history_edu_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('4. Bộ Nhớ Quyết Định'),
                            ],
                          ),
                        ),
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.verified_user_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('5. Thẩm Định Stage-Gate'),
                            ],
                          ),
                        ),
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.loop_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('6. Vòng Lặp 12WY Loop'),
                            ],
                          ),
                        ),
                        Tab(
                          height: 34,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.rate_review_outlined, size: 15),
                              SizedBox(width: 6),
                              Text('Review tuần'),
                            ],
                          ),
                        ),
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
                  ValidationStudioTab(),
                  StrategyLensesTab(),
                  EvidenceBackboneTab(),
                  DecisionLogTab(),
                  StageGateAuditTab(),
                  TwelveWyLoopTab(),
                  WeeklyReviewTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

