import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../../core/theme/app_theme.dart';
import 'widgets/floating_voice_hologram.dart';
import 'widgets/dashboard_sidebar.dart';
import 'widgets/dashboard_top_bar.dart';
import 'widgets/dashboard_content_body.dart';

class DashboardView extends GetView<DashboardController> {
  const DashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    final bool isDesktop = MediaQuery.of(context).size.width >= 800;

    if (isDesktop) {
      return Scaffold(
        body: Container(
          decoration: const BoxDecoration(
            gradient: AppTheme.backgroundLinearGradient,
          ),
          child: Stack(
            children: [
              Padding(
                padding: const EdgeInsets.all(12.0),
                child: Row(
                  children: [
                    DashboardDesktopSidebar(controller: controller),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DashboardContentBody(controller: controller),
                    ),
                  ],
                ),
              ),
              const FloatingVoiceHologram(),
            ],
          ),
        ),
      );
    }

    // Mobile layout
    final GlobalKey<ScaffoldState> scaffoldKey = GlobalKey<ScaffoldState>();

    return Scaffold(
      key: scaffoldKey,
      drawer: DashboardMobileDrawer(controller: controller),
      appBar: DashboardMobileAppBar(
        scaffoldKey: scaffoldKey,
        controller: controller,
      ),
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: AppTheme.backgroundLinearGradient,
            ),
            child: DashboardContentBody(controller: controller),
          ),
          const FloatingVoiceHologram(),
        ],
      ),
    );
  }
}
