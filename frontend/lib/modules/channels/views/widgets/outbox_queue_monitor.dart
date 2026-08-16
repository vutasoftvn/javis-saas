import 'package:flutter/material.dart';

class OutboxQueueMonitor extends StatelessWidget {
  final List<dynamic> outboxItems;
  final Function(String outboxId)? onRetry;
  final VoidCallback? onProcessBatch;

  const OutboxQueueMonitor({
    super.key,
    required this.outboxItems,
    this.onRetry,
    this.onProcessBatch,
  });

  @override
  Widget build(BuildContext context) {
    if (outboxItems.isEmpty) {
      return Container(
        height: 250,
        alignment: Alignment.center,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.outbox_rounded, size: 40, color: Color(0xFF475569)),
            const SizedBox(height: 10),
            const Text(
              'Hàng đợi Outbox hiện đang trống.',
              style: TextStyle(color: Color(0xFF64748B), fontSize: 14),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'HÀNG ĐỢI GỬI TIN BỀN VỮNG (${outboxItems.length})',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
            if (onProcessBatch != null)
              ElevatedButton.icon(
                onPressed: onProcessBatch,
                icon: const Icon(Icons.send_rounded, size: 14, color: Colors.black),
                label: const Text('Xử lý ngay', style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00E5FF),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: outboxItems.length,
          separatorBuilder: (context, index) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final item = outboxItems[index] as Map<String, dynamic>;
            return _buildOutboxItem(context, item);
          },
        ),
      ],
    );
  }

  Widget _buildOutboxItem(BuildContext context, Map<String, dynamic> item) {
    final id = item['id']?.toString() ?? '';
    final channel = item['channel']?.toString() ?? 'email';
    final status = (item['status']?.toString() ?? 'pending').toLowerCase();
    final dedupeKey = item['dedupe_key']?.toString() ?? '';
    final error = item['error']?.toString();
    final preview = item['payload_preview']?.toString() ?? '';

    Color statusColor;
    String statusText;
    switch (status) {
      case 'sent':
        statusColor = const Color(0xFF10B981);
        statusText = 'ĐÃ GỬI';
        break;
      case 'failed':
        statusColor = const Color(0xFFEF4444);
        statusText = 'LỖI';
        break;
      case 'pending':
      default:
        statusColor = const Color(0xFFF59E0B);
        statusText = 'CHỜ GỬI';
        break;
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              channel == 'telegram'
                  ? Icons.send_rounded
                  : channel == 'zalo'
                      ? Icons.chat_rounded
                      : Icons.email_rounded,
              color: statusColor,
              size: 18,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        channel.toUpperCase(),
                        style: const TextStyle(
                          color: Color(0xFF38BDF8),
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        dedupeKey,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        statusText,
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  preview,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                ),
                if (error != null && error.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Lỗi: $error',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Color(0xFFEF4444), fontSize: 10),
                  ),
                ],
              ],
            ),
          ),
          if (status == 'failed' && onRetry != null) ...[
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.refresh_rounded, color: Color(0xFF38BDF8), size: 18),
              tooltip: 'Thử gửi lại',
              onPressed: () => onRetry?.call(id),
            ),
          ],
        ],
      ),
    );
  }
}
