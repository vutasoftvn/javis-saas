import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/ai_operations_controller.dart';

class ExecutionHealthTab extends GetView<AiOperationsController> {
  const ExecutionHealthTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final health = controller.health.value;
      final provider = health?['provider'] ?? 'mock';
      final isAvailable = health?['available'] == true;

      return SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSecurityHeaderCard(isAvailable),
            const SizedBox(height: 16),
            _buildStatusOverview(provider, isAvailable),
            const SizedBox(height: 16),
            _buildSecurityRulesCard(),
          ],
        ),
      );
    });
  }

  Widget _buildSecurityHeaderCard(bool isAvailable) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isAvailable ? AppTheme.success.withValues(alpha: 0.4) : AppTheme.warning.withValues(alpha: 0.4),
        ),
        gradient: LinearGradient(
          colors: [
            (isAvailable ? AppTheme.success : AppTheme.warning).withValues(alpha: 0.1),
            AppTheme.surfaceDark,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: (isAvailable ? AppTheme.success : AppTheme.warning).withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isAvailable ? Icons.shield_outlined : Icons.gpp_maybe_outlined,
              color: isAvailable ? AppTheme.success : AppTheme.warning,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Môi trường thực thi: An toàn',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isAvailable
                      ? 'Tất cả tác vụ phân tích và chạy code được cô lập hoàn toàn trong Sandbox ephemeral.'
                      : 'Hệ thống đang ở chế độ dự phòng an toàn.',
                  style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13.5),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusOverview(String provider, bool isAvailable) {
    return Row(
      children: [
        Expanded(
          child: _buildMetricCard(
            title: 'Trạng thái Runtime',
            value: isAvailable ? 'Sẵn sàng' : 'Không khả dụng',
            icon: Icons.check_circle_outline,
            color: isAvailable ? AppTheme.success : AppTheme.error,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            title: 'Provider',
            value: provider.toUpperCase(),
            icon: Icons.hub_outlined,
            color: AppTheme.primary,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            title: 'Chính sách cô lập',
            value: 'Job Ephemeral',
            icon: Icons.lock_outline,
            color: AppTheme.secondary,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSecurityRulesCard() {
    final rules = [
      {'title': 'Zero Host Execution', 'desc': 'Không chạy bất kỳ script tùy ý nào trên máy chủ COSA.'},
      {'title': 'Network Egress Deny', 'desc': 'Mặc định chặn toàn bộ mạng internet, chỉ mở domain allowlist cho research.'},
      {'title': 'Private LAN Protection', 'desc': 'Chặn vĩnh viễn truy cập tới mạng nội bộ (10/8, 172.16/12, 192.168/16) và Metadata IP.'},
      {'title': 'Ephemeral Sandbox Lifecycle', 'desc': 'Sandbox được tạo riêng theo từng Job và tự động hủy ngay sau khi thu thập file kết quả.'},
      {'title': 'Automated Secret Redaction', 'desc': 'Tự động che giấu toàn bộ API Key, Token và thông tin nhạy cảm trước khi lưu log.'},
    ];

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Quy chuẩn bảo mật & cô lập thực thi',
            style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          ...rules.map((r) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.shield, color: AppTheme.primary, size: 16),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        r['title']!,
                        style: const TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        r['desc']!,
                        style: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          )),
        ],
      ),
    );
  }
}
