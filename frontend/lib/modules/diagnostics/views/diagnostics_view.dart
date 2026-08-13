import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/diagnostics_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/floating_app_bar.dart';

class DiagnosticsView extends GetView<DiagnosticsController> {
  const DiagnosticsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<DiagnosticsController>()) {
      Get.put(DiagnosticsController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Top Floating AppBar Card
          JavisFloatingAppBar(
            title: 'Chẩn đoán hệ thống',
            subtitle: 'Kiểm tra trạng thái kết nối và hiệu năng các dịch vụ nền',
            icon: Icons.monitor_heart_rounded,
            actions: [
              IconButton(
                onPressed: controller.loadData,
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

              final data = controller.diagnosticsData.value;
              if (data == null) {
                return const Center(child: Text('Không thể tải dữ liệu chẩn đoán.', style: TextStyle(color: AppTheme.error)));
              }

              return SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Trạng thái', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(child: _buildStatusCard('Hệ thống', data['status'] == 'ok')),
                        const SizedBox(width: 16),
                        Expanded(child: _buildStatusCard('Tiến trình nền (Workers)', data['workers'] == 'healthy')),
                        const SizedBox(width: 16),
                        Expanded(child: _buildStatusCard('Kết nối (Connectors)', data['connectors'] == 'healthy')),
                      ],
                    ),
                    const SizedBox(height: 32),
                    const Text('Mức sử dụng tài nguyên', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(child: _buildMetricCard('Số lần chạy AI', '${data['usage']?['ai_runs'] ?? 0}', Icons.psychology)),
                        const SizedBox(width: 16),
                        Expanded(child: _buildMetricCard('Tác vụ', '${data['usage']?['tasks'] ?? 0}', Icons.check_box)),
                      ],
                    ),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusCard(String title, bool isHealthy) {
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
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: (isHealthy ? AppTheme.success : AppTheme.error).withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(
                isHealthy ? Icons.check_circle : Icons.error,
                color: isHealthy ? AppTheme.success : AppTheme.error,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 14)),
                  const SizedBox(height: 4),
                  Text(
                    isHealthy ? 'Hoạt động tốt' : 'Lỗi',
                    style: TextStyle(
                      color: isHealthy ? AppTheme.success : AppTheme.error,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard(String title, String value, IconData icon) {
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
                Icon(icon, color: AppTheme.primaryLight, size: 20),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 14)),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              value,
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: AppTheme.textDark),
            ),
          ],
        ),
      ),
    );
  }
}
