import 'package:flutter/material.dart';
import '../../../data/models/pmf_scoreboard_model.dart';

class MaturityTrackPanel extends StatelessWidget {
  final MaturityAssessment? assessment;
  final bool isLoading;

  const MaturityTrackPanel({
    super.key,
    required this.assessment,
    this.isLoading = false,
  });

  Color _getLevelColor(MaturityLevel level) {
    switch (level) {
      case MaturityLevel.governed:
        return Colors.green;
      case MaturityLevel.repeatable:
        return Colors.blue;
      case MaturityLevel.early:
        return Colors.amber.shade800;
      case MaturityLevel.notAssessed:
      case MaturityLevel.unknown:
        return Colors.grey;
    }
  }

  String _getLevelLabel(MaturityLevel level) {
    switch (level) {
      case MaturityLevel.governed:
        return 'GOVERNED (Chuẩn hóa)';
      case MaturityLevel.repeatable:
        return 'REPEATABLE (Lặp lại)';
      case MaturityLevel.early:
        return 'EARLY (Sơ khởi)';
      case MaturityLevel.notAssessed:
        return 'NOT ASSESSED (Chưa đánh giá)';
      case MaturityLevel.unknown:
        return 'UNKNOWN';
    }
  }

  Widget _buildDimensionTile({
    required String title,
    required IconData icon,
    required MaturityDimension dimension,
  }) {
    final color = _getLevelColor(dimension.level);

    return ExpansionTile(
      leading: Icon(icon, color: color),
      title: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
      ),
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.5)),
        ),
        child: Text(
          _getLevelLabel(dimension.level),
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.bold,
            fontSize: 11,
          ),
        ),
      ),
      childrenPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            'Cơ sở đánh giá: ${dimension.rationale}',
            style: const TextStyle(fontSize: 12, color: Colors.black87),
          ),
        ),
        if (dimension.missingEvidence.isNotEmpty) ...[
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Bằng chứng còn thiếu:',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: Colors.red.shade800,
              ),
            ),
          ),
          const SizedBox(height: 4),
          ...dimension.missingEvidence.map(
            (missing) => Padding(
              padding: const EdgeInsets.only(left: 8, bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: TextStyle(color: Colors.red)),
                  Expanded(
                    child: Text(
                      missing,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey.shade800,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (assessment == null) {
      return Card(
        margin: const EdgeInsets.all(16),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: const [
              Icon(Icons.track_changes, size: 48, color: Colors.grey),
              SizedBox(height: 16),
              Text(
                'Chưa có Đánh Giá Trưởng Thành (Maturity Track)',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Đánh giá trưởng thành sẽ được suy diễn tự động từ PMF Scoreboard và bằng chứng.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }

    return Card(
      margin: const EdgeInsets.all(16),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Expanded(
                  child: Text(
                    'Ma Trận Trưởng Thành PMF (5 Dimensions)',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
                Text(
                  'Assessed: ${assessment!.assessedAt.day}/${assessment!.assessedAt.month}/${assessment!.assessedAt.year}',
                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildDimensionTile(
              title: '1. Đo lường & Hợp đồng chỉ số (Measurement)',
              icon: Icons.square_foot,
              dimension: assessment!.measurement,
            ),
            _buildDimensionTile(
              title: '2. Giá trị khách hàng xác thực (Value)',
              icon: Icons.thumb_up_alt_outlined,
              dimension: assessment!.value,
            ),
            _buildDimensionTile(
              title: '3. Tỷ lệ gắn kết & Giữ chân (Retention)',
              icon: Icons.repeat,
              dimension: assessment!.retention,
            ),
            _buildDimensionTile(
              title: '4. Sự sẵn sàng thương mại (Commercial)',
              icon: Icons.monetization_on_outlined,
              dimension: assessment!.commercial,
            ),
            _buildDimensionTile(
              title: '5. Năng lực vận hành học hỏi (Operational)',
              icon: Icons.sync_alt,
              dimension: assessment!.operational,
            ),
          ],
        ),
      ),
    );
  }
}
