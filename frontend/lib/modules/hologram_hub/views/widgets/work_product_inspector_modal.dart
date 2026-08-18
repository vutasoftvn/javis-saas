import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';

class WorkProductInspectorModal extends StatelessWidget {
  final List<Map<String, dynamic>> workProducts;
  final Function(int workProductId) onAccept;
  final VoidCallback onClose;

  const WorkProductInspectorModal({
    super.key,
    required this.workProducts,
    required this.onAccept,
    required this.onClose,
  });

  static void show(BuildContext context, {
    required List<Map<String, dynamic>> workProducts,
    required Function(int workProductId) onAccept,
  }) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (ctx) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 850, maxHeight: 680),
          child: WorkProductInspectorModal(
            workProducts: workProducts,
            onAccept: (id) {
              onAccept(id);
              Navigator.of(ctx).pop();
            },
            onClose: () => Navigator.of(ctx).pop(),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: GlassCard(
        borderRadius: 20,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFF10B981).withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Icon(
                    Icons.assignment_turned_in_outlined,
                    color: Color(0xFF10B981),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Thành Phẩm Bàn Giao & Quyết Định (Work Products & ADR)',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'Tổng số ${workProducts.length} tài liệu bàn giao từ các AI Agent',
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: onClose,
                  icon: const Icon(Icons.close, color: Color(0xFF94A3B8)),
                  tooltip: 'Đóng',
                ),
              ],
            ),
            const SizedBox(height: 20),
            const Divider(color: Color(0xFF1E293B), height: 1),
            const SizedBox(height: 16),

            // Content List
            Expanded(
              child: workProducts.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.folder_open_outlined,
                            size: 54,
                            color: const Color(0xFF64748B).withValues(alpha: 0.6),
                          ),
                          const SizedBox(height: 14),
                          const Text(
                            'Chưa có thành phẩm nào',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Các báo cáo, tài liệu và phân tích của Agent sau khi hoàn thành sẽ xuất hiện tại đây.',
                            style: TextStyle(
                              color: Color(0xFF64748B),
                              fontSize: 12,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    )
                  : ListView.separated(
                      itemCount: workProducts.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 14),
                      itemBuilder: (context, idx) {
                        return _buildProductCard(context, workProducts[idx]);
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProductCard(BuildContext context, Map<String, dynamic> product) {
    final id = (product['id'] as num?)?.toInt() ?? 0;
    final title = (product['title'] as String?) ?? 'Bản thành phẩm không tên';
    final productType = (product['product_type'] as String?) ?? 'DOCUMENT';
    final status = (product['status'] as String?) ?? 'DRAFT';
    final authorKey = (product['author_agent_key'] as String?) ?? 'AI Specialist';
    final summary = (product['content_markdown'] as String?) ?? (product['summary'] as String?) ?? 'Không có mô tả chi tiết.';
    final isAccepted = status.toUpperCase() == 'ACCEPTED';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isAccepted
              ? const Color(0xFF10B981).withValues(alpha: 0.4)
              : const Color(0xFF14B8A6).withValues(alpha: 0.25),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF14B8A6).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  productType.toUpperCase(),
                  style: const TextStyle(
                    color: Color(0xFF14B8A6),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isAccepted
                      ? const Color(0xFF10B981).withValues(alpha: 0.15)
                      : const Color(0xFFF59E0B).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  isAccepted ? 'ĐÃ NGHIỆM THU' : 'CHỜ NGHIỆM THU',
                  style: TextStyle(
                    color: isAccepted ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Title & Author
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Tác giả: $authorKey',
            style: const TextStyle(
              color: Color(0xFF38BDF8),
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 8),

          // Markdown / Summary Content snippet
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              summary,
              style: const TextStyle(
                color: Color(0xFFCBD5E1),
                fontSize: 12,
                height: 1.4,
              ),
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 12),

          // Action
          if (!isAccepted)
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton.icon(
                onPressed: () => onAccept(id),
                icon: const Icon(Icons.check, size: 16),
                label: const Text('Nghiệm thu (Accept)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
