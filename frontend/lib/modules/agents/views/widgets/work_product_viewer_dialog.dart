import 'dart:convert';
import 'package:flutter/material.dart';
import '../../../../data/services/agent_platform_service.dart';

class WorkProductViewerDialog extends StatefulWidget {
  const WorkProductViewerDialog({super.key});

  @override
  State<WorkProductViewerDialog> createState() => _WorkProductViewerDialogState();
}

class _WorkProductViewerDialogState extends State<WorkProductViewerDialog> {
  final AgentPlatformService _service = AgentPlatformService();
  bool _isLoading = true;
  List<Map<String, dynamic>> _workProducts = [];

  @override
  void initState() {
    super.initState();
    _loadWorkProducts();
  }

  Future<void> _loadWorkProducts() async {
    setState(() => _isLoading = true);
    final list = await _service.listWorkProducts();
    setState(() {
      _workProducts = list;
      _isLoading = false;
    });
  }

  Future<void> _acceptWorkProduct(int id) async {
    final res = await _service.acceptWorkProduct(id);
    if (mounted) {
      if (res != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã nghiệm thu sản phẩm bàn giao!'), backgroundColor: Color(0xFF10B981)),
        );
        _loadWorkProducts();
      }
    }
  }

  Future<void> _requestRevision(int id) async {
    final ctrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Yêu cầu chỉnh sửa Work Product', style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Nhập lý do và hướng dẫn chỉnh sửa để Agent viết lại:', style: TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 12),
            TextField(
              controller: ctrl,
              maxLines: 3,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Nhập feedback...',
                hintStyle: TextStyle(color: Colors.grey.shade600),
                filled: true,
                fillColor: const Color(0xFF0F172A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy', style: TextStyle(color: Colors.grey))),
          ElevatedButton(
            onPressed: () async {
              if (ctrl.text.trim().isNotEmpty) {
                Navigator.pop(ctx);
                await _service.requestWorkProductRevision(id, feedback: ctrl.text.trim());
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Đã gửi yêu cầu chỉnh sửa cho Agent!'), backgroundColor: Color(0xFF6366F1)),
                  );
                  _loadWorkProducts();
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
            child: const Text('Gửi phản hồi', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 860,
        height: 640,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.purpleAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.inventory_2_outlined, color: Colors.purpleAccent, size: 22),
                ),
                const SizedBox(width: 14),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Work Products & Deliverables Vault',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                      Text(
                        'Sản phẩm bàn giao định kiểu, lưu vết kiểm toán và nghiệm thu từ Agent Workforce',
                        style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close_rounded, color: Colors.grey),
                ),
              ],
            ),

            const SizedBox(height: 18),

            // Content
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: Colors.purpleAccent))
                  : _workProducts.isEmpty
                      ? Center(
                          child: Text('Chưa có sản phẩm bàn giao nào được sinh ra.', style: TextStyle(color: Colors.grey.shade500)),
                        )
                      : ListView.separated(
                          itemCount: _workProducts.length,
                          separatorBuilder: (context, index) => const SizedBox(height: 12),
                          itemBuilder: (ctx, i) {
                            final wp = _workProducts[i];
                            final id = wp['id'] is int ? wp['id'] as int : int.tryParse(wp['id'].toString()) ?? 0;
                            final title = wp['title'] ?? 'Untitled Work Product';
                            final type = wp['product_type'] ?? 'DOCUMENT';
                            final status = (wp['status'] ?? 'DRAFT').toString().toUpperCase();
                            final agent = wp['agent_key'] ?? 'Agent';
                            final summary = wp['summary'] ?? '';
                            final content = wp['content_jsonb'] ?? {};

                            final isAccepted = status == 'ACCEPTED';
                            final statusColor = isAccepted ? const Color(0xFF10B981) : Colors.amber;

                            return Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: const Color(0xFF1E293B),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFF334155)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: Colors.purpleAccent.withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(type, style: const TextStyle(color: Colors.purpleAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          title,
                                          style: const TextStyle(color: Colors.white, fontSize: 14.5, fontWeight: FontWeight.w700),
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: statusColor.withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(status, style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.w800)),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Text('Tác giả: $agent', style: TextStyle(color: Colors.grey.shade400, fontSize: 12)),
                                  if (summary.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    Text(summary, style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 13)),
                                  ],
                                  const SizedBox(height: 12),
                                  // Content Accordion
                                  ExpansionTile(
                                    tilePadding: EdgeInsets.zero,
                                    title: const Text('Xem nội dung chi tiết', style: TextStyle(color: Colors.blueAccent, fontSize: 12)),
                                    children: [
                                      Container(
                                        width: double.infinity,
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFF020617),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: SelectableText(
                                          const JsonEncoder.withIndent('  ').convert(content),
                                          style: const TextStyle(color: Color(0xFF94A3B8), fontFamily: 'monospace', fontSize: 11.5),
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (!isAccepted) ...[
                                    const Divider(color: Color(0xFF334155), height: 16),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.end,
                                      children: [
                                        OutlinedButton(
                                          onPressed: () => _requestRevision(id),
                                          style: OutlinedButton.styleFrom(
                                            side: const BorderSide(color: Color(0xFF6366F1)),
                                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                          ),
                                          child: const Text('Yêu cầu sửa lại', style: TextStyle(color: Color(0xFF818CF8), fontSize: 12)),
                                        ),
                                        const SizedBox(width: 10),
                                        ElevatedButton(
                                          onPressed: () => _acceptWorkProduct(id),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: const Color(0xFF10B981),
                                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                          ),
                                          child: const Text('Nghiệm thu (Accept)', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                                        ),
                                      ],
                                    ),
                                  ],
                                ],
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
