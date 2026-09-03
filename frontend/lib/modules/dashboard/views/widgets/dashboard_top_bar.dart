import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/dashboard_controller.dart';
import '../../models/dashboard_nav_config.dart';

class DashboardMobileAppBar extends StatelessWidget implements PreferredSizeWidget {
  final GlobalKey<ScaffoldState> scaffoldKey;
  final DashboardController controller;

  const DashboardMobileAppBar({
    super.key,
    required this.scaffoldKey,
    required this.controller,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight + 1);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: AppTheme.surfaceDarkHeader,
      elevation: 0,
      leading: IconButton(
        icon: const Icon(Icons.menu_rounded, color: Colors.white),
        onPressed: () => scaffoldKey.currentState?.openDrawer(),
      ),
      title: Obx(() {
        final idx = controller.currentIndex.value;
        return Text(
          DashboardNavConfig.getPageTitle(idx),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
        );
      }),
      actions: [
        TextButton.icon(
          onPressed: () {
            controller.changePage(0, 0);
            if (Get.currentRoute != AppRoutes.hub) {
              Get.offNamed(AppRoutes.hub);
            }
          },
          icon: const Icon(Icons.psychology, size: 20, color: Color(0xFF14B8A6)),
          label: const Text(
            'Hologram',
            style: TextStyle(
              color: Color(0xFF14B8A6),
              fontSize: 13,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(width: 6),
      ],
      bottom: const PreferredSize(
        preferredSize: Size.fromHeight(1),
        child: Divider(height: 1, thickness: 1, color: AppTheme.borderDark),
      ),
    );
  }
}
