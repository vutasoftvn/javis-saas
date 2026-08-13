import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/sales_today_controller.dart';

class SalesTodayView extends StatelessWidget {
  const SalesTodayView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<SalesTodayController>()) {
      Get.put(SalesTodayController());
    }
    final c = Get.find<SalesTodayController>();

    return Obx(() {
      if (c.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }

      final pipelineVal = c.funnelMetrics['pipeline_value'] ?? 0.0;
      final weightedVal = c.funnelMetrics['weighted_pipeline'] ?? 0.0;
      final totalLeads = c.funnelMetrics['total_leads'] ?? 0;
      final qualifiedLeads = c.funnelMetrics['qualified_leads'] ?? 0;

      return RefreshIndicator(
        onRefresh: c.refreshData,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // KPI Summary Cards
            Row(
              children: [
                Expanded(
                  child: _buildMetricCard(
                    context,
                    title: 'Giá trị Phễu',
                    value: '\$${pipelineVal.toStringAsFixed(0)}',
                    subtitle: 'Trọng số: \$${weightedVal.toStringAsFixed(0)}',
                    color: Colors.blue.shade700,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricCard(
                    context,
                    title: 'Manh mối Hoạt động',
                    value: '$totalLeads',
                    subtitle: 'Đạt chuẩn: $qualifiedLeads',
                    color: Colors.green.shade700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Open Opportunities List Section
            Text(
              'Cơ hội bán hàng đang mở (${c.openOpportunities.length})',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if (c.openOpportunities.isEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Center(
                    child: Text(
                      'Chưa có cơ hội bán hàng nào',
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                  ),
                ),
              )
            else
              ...c.openOpportunities.map((opp) {
                final prod = opp['product'] ?? 'Cơ hội chưa đặt tên';
                final stage = opp['stage'] ?? 'DISCOVERY';
                final val = opp['estimated_value'] ?? 0.0;
                final prob = (opp['probability'] ?? 0.0) * 100;
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(prod, style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text('Giai đoạn: $stage • Xác suất: ${prob.toStringAsFixed(0)}%'),
                    trailing: Text(
                      '\$${val.toStringAsFixed(0)}',
                      style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue.shade800),
                    ),
                  ),
                );
              }),
          ],
        ),
      );
    });
  }

  Widget _buildMetricCard(
    BuildContext context, {
    required String title,
    required String value,
    required String subtitle,
    required Color color,
  }) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
            const SizedBox(height: 4),
            Text(value, style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(subtitle, style: TextStyle(color: Colors.grey.shade600, fontSize: 11)),
          ],
        ),
      ),
    );
  }
}
