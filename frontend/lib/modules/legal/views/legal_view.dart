import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/legal_controller.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class LegalView extends StatelessWidget {
  const LegalView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<LegalController>()) {
      Get.put(LegalController());
    }
    final c = Get.find<LegalController>();

    return Obx(() {
      final statusMap = c.status;
      final openChecklist = statusMap['open_checklist_items'] ?? 0;
      final openObligations = statusMap['open_obligations'] ?? 0;
      final rawFunc = statusMap['function']?.toString() ?? 'LEGAL';
      final funcName = rawFunc.toUpperCase() == 'LEGAL' ? 'Pháp lý' : rawFunc;

      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          JavisFloatingAppBar(
            title: 'Bộ phận Pháp lý',
            subtitle: 'Quản lý tuân thủ, quy định & nghĩa vụ pháp lý',
            icon: Icons.gavel_rounded,
            actions: [
              Container(
                decoration: const BoxDecoration(
                  color: AppTheme.primary,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  tooltip: 'Tải lại dữ liệu',
                  icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                  onPressed: c.load,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _buildMetricCard(
                        context,
                        title: 'Bộ phận',
                        value: funcName,
                        icon: Icons.business_center_outlined,
                        color: Colors.tealAccent,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _buildMetricCard(
                        context,
                        title: 'Hạng mục kiểm tra đang mở',
                        value: '$openChecklist',
                        icon: Icons.fact_check_outlined,
                        color: openChecklist > 0 ? Colors.amberAccent : Colors.tealAccent,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _buildMetricCard(
                        context,
                        title: 'Nghĩa vụ pháp lý đang mở',
                        value: '$openObligations',
                        icon: Icons.shield_outlined,
                        color: openObligations > 0 ? Colors.amberAccent : Colors.tealAccent,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                  ),
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Chi tiết trạng thái',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                      ),
                      const SizedBox(height: 16),
                      _buildStatusRow('Chức năng', funcName, Icons.account_tree_outlined),
                      const Divider(color: Colors.white10),
                      _buildStatusRow('Hạng mục kiểm tra đang mở', '$openChecklist', Icons.checklist_rtl_rounded),
                      const Divider(color: Colors.white10),
                      _buildStatusRow('Nghĩa vụ pháp lý đang mở', '$openObligations', Icons.gavel_outlined),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      );
    });
  }

  Widget _buildMetricCard(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 13, fontWeight: FontWeight.w500),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(icon, color: color, size: 20),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusRow(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.tealAccent),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
          ),
          Text(
            value,
            style: const TextStyle(color: Colors.tealAccent, fontWeight: FontWeight.bold, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
