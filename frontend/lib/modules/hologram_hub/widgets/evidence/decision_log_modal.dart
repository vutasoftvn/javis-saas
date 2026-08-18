import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';

class DecisionLogModal extends StatefulWidget {
  final int? projectId;
  final List<StrategicDecisionModel> decisions;
  final Function(String query) onSearchMemory;
  final Function(Map<String, dynamic>) onRecordDecision;

  const DecisionLogModal({
    super.key,
    this.projectId,
    required this.decisions,
    required this.onSearchMemory,
    required this.onRecordDecision,
  });

  static Future<void> show(
    BuildContext context, {
    int? projectId,
    required List<StrategicDecisionModel> decisions,
    required Function(String query) onSearchMemory,
    required Function(Map<String, dynamic>) onRecordDecision,
  }) {
    return showDialog(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => Dialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: Color(0xFF334155), width: 1.5),
        ),
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 760, maxHeight: 780),
          child: DecisionLogModal(
            projectId: projectId,
            decisions: decisions,
            onSearchMemory: onSearchMemory,
            onRecordDecision: onRecordDecision,
          ),
        ),
      ),
    );
  }

  @override
  State<DecisionLogModal> createState() => _DecisionLogModalState();
}

class _DecisionLogModalState extends State<DecisionLogModal> {
  final TextEditingController _searchCtrl = TextEditingController();

  void _showCreateDecisionDialog() {
    final questionCtrl = TextEditingController();
    final optionCtrl = TextEditingController();
    final alternativesCtrl = TextEditingController();
    final rationaleCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        title: const Text('Ghi Nhận Quyết Định Chiến Lược', style: TextStyle(color: Colors.white)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Vấn đề / Câu hỏi chiến lược:', style: TextStyle(color: Colors.white70, fontSize: 12)),
              const SizedBox(height: 4),
              TextField(
                controller: questionCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: Tập trung phân khúc B2B hay B2C?',
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.06),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(height: 12),
              const Text('Phương án đã chọn (Selected Option):', style: TextStyle(color: Colors.white70, fontSize: 12)),
              const SizedBox(height: 4),
              TextField(
                controller: optionCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: Pivot 100% sang B2B',
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.06),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(height: 12),
              const Text('Các phương án đã loại bỏ (cách nhau bởi dấu phẩy):', style: TextStyle(color: Colors.white70, fontSize: 12)),
              const SizedBox(height: 4),
              TextField(
                controller: alternativesCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: Giữ cả 2, Chỉ làm B2C...',
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.06),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(height: 12),
              const Text('Lý do cốt lõi & Căn cứ thực tế (Rationale):', style: TextStyle(color: Colors.white70, fontSize: 12)),
              const SizedBox(height: 4),
              TextField(
                controller: rationaleCtrl,
                maxLines: 3,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: Biên lợi nhuận gộp B2B đạt 78%...',
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.06),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981), foregroundColor: Colors.white),
            onPressed: () {
              if (questionCtrl.text.trim().isNotEmpty && optionCtrl.text.trim().isNotEmpty) {
                final alts = alternativesCtrl.text
                    .split(',')
                    .map((s) => s.trim())
                    .where((s) => s.isNotEmpty)
                    .toList();

                widget.onRecordDecision({
                  'project_id': widget.projectId,
                  'question': questionCtrl.text.trim(),
                  'selected_option': optionCtrl.text.trim(),
                  'alternatives': alts,
                  'rationale': rationaleCtrl.text.trim(),
                });
                Navigator.of(ctx).pop();
              }
            },
            child: const Text('Lưu Quyết Định', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
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
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.4)),
                ),
                child: const Icon(Icons.history_edu_outlined, color: Color(0xFF10B981), size: 24),
              ),
              const SizedBox(width: 14),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'BỘ NHỚ QUYẾT ĐỊNH CÔNG TY (COMPANY MEMORY)',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'Lưu vết Decision Lineage kèm Bằng chứng minh chứng cho AI',
                      style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                ),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('+ Ghi Quyết Định', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                onPressed: _showCreateDecisionDialog,
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.white70),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Search Company Memory Bar
          TextField(
            controller: _searchCtrl,
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Tra cứu: Vì sao chúng ta quyết định chọn B2B? Tại sao đặt giá \$150?...',
              hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.35), fontSize: 13),
              prefixIcon: const Icon(Icons.search, color: Color(0xFF38BDF8), size: 20),
              filled: true,
              fillColor: const Color(0xFF1E293B).withValues(alpha: 0.6),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFF334155)),
              ),
              contentPadding: const EdgeInsets.symmetric(vertical: 12),
            ),
            onSubmitted: widget.onSearchMemory,
          ),
          const SizedBox(height: 16),
          const Divider(color: Color(0xFF334155), height: 1),
          const SizedBox(height: 14),

          // List of Decisions
          Expanded(
            child: widget.decisions.isEmpty
                ? Center(
                    child: Text(
                      'Chưa có quyết định nào được ghi nhận. Bấm "+ Ghi Quyết Định" để bắt đầu xây dựng Company Memory!',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                  )
                : ListView.builder(
                    itemCount: widget.decisions.length,
                    itemBuilder: (ctx, i) {
                      final d = widget.decisions[i];
                      return Container(
                        margin: const EdgeInsets.only(bottom: 14),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B).withValues(alpha: 0.5),
                          borderRadius: BorderRadius.circular(14),
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
                                    color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    d.stage,
                                    style: const TextStyle(
                                      color: Color(0xFF38BDF8),
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                const Spacer(),
                                Text(
                                  '${d.createdAt.day}/${d.createdAt.month}/${d.createdAt.year}',
                                  style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 11),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              d.question ?? d.decision,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),

                            // Selected Option
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: const Color(0xFF10B981).withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.35)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.check_circle, size: 14, color: Color(0xFF10B981)),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      'Phương án chọn: ${d.selectedOption ?? d.decision}',
                                      style: const TextStyle(
                                        color: Color(0xFF34D399),
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),

                            // Alternatives
                            if (d.alternatives.isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 6,
                                runSpacing: 4,
                                children: d.alternatives.map((alt) => Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: Colors.white.withValues(alpha: 0.04),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        'Đã loại bỏ: $alt',
                                        style: TextStyle(
                                          color: Colors.white.withValues(alpha: 0.45),
                                          fontSize: 11,
                                          decoration: TextDecoration.lineThrough,
                                        ),
                                      ),
                                    )).toList(),
                              ),
                            ],

                            // Rationale
                            if (d.rationale != null && d.rationale!.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(
                                'Căn cứ: ${d.rationale!}',
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.75),
                                  fontSize: 12,
                                  fontStyle: FontStyle.italic,
                                ),
                              ),
                            ],

                            // Evidence Refs Count
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Icon(Icons.verified_outlined, size: 13, color: const Color(0xFF10B981).withValues(alpha: 0.8)),
                                const SizedBox(width: 4),
                                Text(
                                  '${d.evidenceRefs.length} bằng chứng thực tế minh chứng',
                                  style: const TextStyle(
                                    color: Color(0xFF10B981),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ],
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
