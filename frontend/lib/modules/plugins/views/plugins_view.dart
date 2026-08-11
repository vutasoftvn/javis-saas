import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/plugins_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/floating_app_bar.dart';

class PluginsView extends GetView<PluginsController> {
  const PluginsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<PluginsController>()) {
      Get.put(PluginsController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Top Floating AppBar Card
          JavisFloatingAppBar(
            title: 'Quản lý Plugins',
            subtitle: 'Mở rộng khả năng xử lý của các trợ lý AI',
            icon: Icons.extension_rounded,
            actions: [
              IconButton(
                onPressed: controller.loadPlugins,
                icon: const Icon(Icons.refresh, color: AppTheme.primary),
                tooltip: 'Làm mới',
              ),
            ],
          ),
          
          // Content
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              if (controller.plugins.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.extension_outlined, size: 64, color: AppTheme.textMutedDark.withValues(alpha: 0.5)),
                      const SizedBox(height: 16),
                      const Text('Chưa có Plugin nào', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 16)),
                    ],
                  ),
                );
              }

              return GridView.builder(
                padding: const EdgeInsets.all(24),
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 350,
                  mainAxisExtent: 180,
                  crossAxisSpacing: 24,
                  mainAxisSpacing: 24,
                ),
                itemCount: controller.plugins.length,
                itemBuilder: (context, index) {
                  final plugin = controller.plugins[index];
                  return _buildPluginCard(context, plugin);
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildPluginCard(BuildContext context, Map<String, dynamic> plugin) {
    return Glassmorphism(
      blur: 20,
      opacity: 0.15,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.secondary.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.extension, color: AppTheme.secondaryLight, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        plugin['slug'] ?? 'Unknown',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        'v${plugin['version'] ?? '1.0.0'}',
                        style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Spacer(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                ElevatedButton.icon(
                  onPressed: () => controller.enablePlugin(plugin['id']),
                  icon: const Icon(Icons.check_circle_outline, size: 16),
                  label: const Text('Bật'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.success.withValues(alpha: 0.2),
                    foregroundColor: AppTheme.success,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: () => controller.disablePlugin(plugin['id']),
                  icon: const Icon(Icons.cancel_outlined, size: 16),
                  label: const Text('Tắt'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.error.withValues(alpha: 0.2),
                    foregroundColor: AppTheme.error,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
