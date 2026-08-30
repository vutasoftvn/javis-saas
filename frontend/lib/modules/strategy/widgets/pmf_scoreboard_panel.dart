import 'package:flutter/material.dart';
import '../../../data/models/pmf_scoreboard_model.dart';

class PmfScoreboardPanel extends StatelessWidget {
  final PmfScoreboardRun? run;
  final bool isLoading;
  final VoidCallback? onRecalculate;

  const PmfScoreboardPanel({
    super.key,
    required this.run,
    this.isLoading = false,
    this.onRecalculate,
  });

  Color _getResultColor(PmfScoreboardResult result) {
    switch (result) {
      case PmfScoreboardResult.promising:
        return Colors.green;
      case PmfScoreboardResult.mixed:
        return Colors.orange;
      case PmfScoreboardResult.concerning:
        return Colors.red;
      case PmfScoreboardResult.insufficientData:
      case PmfScoreboardResult.unknown:
        return Colors.grey;
    }
  }

  String _getResultLabel(PmfScoreboardResult result) {
    switch (result) {
      case PmfScoreboardResult.promising:
        return 'PROMISING (Khả quan)';
      case PmfScoreboardResult.mixed:
        return 'MIXED (Hỗn hợp)';
      case PmfScoreboardResult.concerning:
        return 'CONCERNING (Rủi ro)';
      case PmfScoreboardResult.insufficientData:
        return 'INSUFFICIENT DATA (Thiếu dữ liệu)';
      case PmfScoreboardResult.unknown:
        return 'UNKNOWN';
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (run == null) {
      return Card(
        margin: const EdgeInsets.all(16),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.analytics_outlined, size: 48, color: Colors.grey),
              const SizedBox(height: 16),
              const Text(
                'Chưa có dữ liệu tính toán PMF Scoreboard',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Hệ thống chưa ghi nhận snapshot telemetry hoặc bằng chứng kiểm định nào cho dự án này.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
              if (onRecalculate != null) ...[
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: onRecalculate,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Tính toán PMF Scoreboard'),
                ),
              ],
            ],
          ),
        ),
      );
    }

    final resultColor = _getResultColor(run!.result);

    return Card(
      margin: const EdgeInsets.all(16),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Phân loại kết quả & Nút tính lại
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: resultColor.withOpacity(0.15),
                        border: Border.all(color: resultColor),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        _getResultLabel(run!.result),
                        style: TextStyle(
                          color: resultColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      'Policy: ${run!.policyVersion}',
                      style: const TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                  ],
                ),
                if (onRecalculate != null)
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    tooltip: 'Tính lại bảng điểm',
                    onPressed: onRecalculate,
                  ),
              ],
            ),
            const SizedBox(height: 12),

            // Calculation Hash
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(Icons.fingerprint, size: 16, color: Colors.blueGrey),
                  const SizedBox(width: 6),
                  const Text('Hash: ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                  Expanded(
                    child: Text(
                      run!.calculationHash,
                      style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Missing Data Flags & Reliability Flags
            if (run!.missingDataFlags.isNotEmpty || run!.reliabilityFlags.isNotEmpty) ...[
              const Text(
                'Cảnh báo chất lượng dữ liệu:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  ...run!.missingDataFlags.map(
                    (flag) => Chip(
                      avatar: const Icon(Icons.error_outline, size: 16, color: Colors.red),
                      label: Text('Missing: $flag', style: const TextStyle(fontSize: 12, color: Colors.red)),
                      backgroundColor: Colors.red.shade50,
                      side: BorderSide(color: Colors.red.shade200),
                    ),
                  ),
                  ...run!.reliabilityFlags.map(
                    (flag) => Chip(
                      avatar: const Icon(Icons.warning_amber_outlined, size: 16, color: Colors.orange),
                      label: Text('Flag: $flag', style: const TextStyle(fontSize: 12, color: Colors.orange)),
                      backgroundColor: Colors.orange.shade50,
                      side: BorderSide(color: Colors.orange.shade200),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],

            // Score Components Breakdown
            const Text(
              'Thành phần điểm số (Score Components):',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(height: 8),
            if (run!.scoreComponents.isEmpty)
              const Text(
                'Không có thành phần điểm số nào được ghi nhận.',
                style: TextStyle(color: Colors.grey, fontStyle: FontStyle.italic),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: run!.scoreComponents.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final comp = run!.scoreComponents[index];
                  final isStale = comp.qualityStatus == 'STALE';

                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    leading: Icon(
                      comp.sourceType == 'metric_snapshot' ? Icons.show_chart : Icons.rate_review,
                      color: isStale ? Colors.orange : Colors.blue,
                    ),
                    title: Text(
                      comp.componentKey,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      'Source: ${comp.sourceType} (#${comp.sourceId}) • Quality: ${comp.qualityStatus}',
                      style: TextStyle(
                        fontSize: 11,
                        color: isStale ? Colors.orange.shade800 : Colors.grey.shade600,
                      ),
                    ),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '${(comp.rawScore * 100).toStringAsFixed(1)}%',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                        Text(
                          'Weight: ${comp.weight.toStringAsFixed(1)}',
                          style: const TextStyle(fontSize: 10, color: Colors.grey),
                        ),
                      ],
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
