import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/funnel_controller.dart';

class FunnelView extends StatelessWidget {
  const FunnelView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FunnelController>()) {
      Get.put(FunnelController());
    }
    final c = Get.find<FunnelController>();

    return Obx(() {
      if (c.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }

      return Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Phễu bán hàng', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: c.loadOpportunities,
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: c.stages.length,
              itemBuilder: (context, index) {
                final stage = c.stages[index];
                final stageOpps = c.getOpportunitiesForStage(stage);
                return _buildStageColumn(context, c, stage, stageOpps);
              },
            ),
          ),
        ],
      );
    });
  }

  Widget _buildStageColumn(BuildContext context, FunnelController c, String stage, List<dynamic> opps) {
    return Container(
      width: 260,
      margin: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.blueGrey.shade800,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(stage, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text('${opps.length}', style: const TextStyle(color: Colors.white, fontSize: 11)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.builder(
              itemCount: opps.length,
              itemBuilder: (context, idx) {
                final opp = opps[idx];
                final prod = opp['product'] ?? 'Opportunity';
                final val = opp['estimated_value'] ?? 0.0;

                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(prod, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                        const SizedBox(height: 4),
                        Text('\$${val.toStringAsFixed(0)}', style: TextStyle(color: Colors.blue.shade700, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
