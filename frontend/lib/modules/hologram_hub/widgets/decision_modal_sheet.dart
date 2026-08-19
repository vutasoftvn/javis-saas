import 'package:flutter/material.dart';
import '../../../data/models/founder_decision_model.dart';

class DecisionModalSheet extends StatefulWidget {
  final FounderDecisionModel decision;
  final Function(String optionKey, String? notes) onResolve;

  const DecisionModalSheet({
    Key? key,
    required this.decision,
    required this.onResolve,
  }) : super(key: key);

  @override
  State<DecisionModalSheet> createState() => _DecisionModalSheetState();
}

class _DecisionModalSheetState extends State<DecisionModalSheet> {
  String? selectedOptionKey;
  final TextEditingController notesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Default select AI recommendation or first option
    final pref = widget.decision.aiRecommendation?['preferred_option'];
    if (pref != null && widget.decision.options.any((o) => o.key == pref)) {
      selectedOptionKey = pref;
    } else if (widget.decision.options.isNotEmpty) {
      selectedOptionKey = widget.decision.options.first.key;
    }
  }

  @override
  void dispose() {
    notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final aiRec = widget.decision.aiRecommendation;

    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF59E0B).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFF59E0B), width: 0.8),
                  ),
                  child: Text(
                    widget.decision.domain,
                    style: const TextStyle(color: Color(0xFFFBBF24), fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'Quyết định Chiến lược Founder',
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              widget.decision.question,
              style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600, height: 1.3),
            ),
            if (widget.decision.contextSummary != null) ...[
              const SizedBox(height: 8),
              Text(
                widget.decision.contextSummary!,
                style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 13),
              ),
            ],
            const SizedBox(height: 18),

            // AI Recommendation Box
            if (aiRec != null)
              Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF1E1B4B),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF6366F1).withOpacity(0.4)),
                ),
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.auto_awesome, color: Color(0xFFA5B4FC), size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Khuyến nghị từ COSA Co-Founder:',
                            style: TextStyle(color: Color(0xFFA5B4FC), fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            aiRec['reasoning'] ?? 'Dựa trên phân tích chéo Marketing ROI và Finance Runway.',
                            style: const TextStyle(color: Colors.white, fontSize: 12.5),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 18),
            const Text(
              'Chọn phương án thực thi:',
              style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),

            // Options List
            ...widget.decision.options.map((opt) {
              final isSelected = selectedOptionKey == opt.key;
              return Container(
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(
                  color: isSelected ? const Color(0xFF1E293B) : const Color(0xFF131C2E),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isSelected ? const Color(0xFF6366F1) : const Color(0xFF334155),
                    width: isSelected ? 1.5 : 1.0,
                  ),
                ),
                child: RadioListTile<String>(
                  value: opt.key,
                  groupValue: selectedOptionKey,
                  onChanged: (val) => setState(() => selectedOptionKey = val),
                  activeColor: const Color(0xFF6366F1),
                  title: Text(
                    opt.title,
                    style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w600),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 2),
                      Text(opt.description, style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 12)),
                      if (opt.financialImpact != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Tác động tài chính: ${opt.financialImpact}',
                          style: const TextStyle(color: Color(0xFF34D399), fontSize: 11, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }).toList(),

            const SizedBox(height: 12),
            TextField(
              controller: notesController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Ghi chú thêm cho Workforce (tùy chọn)...',
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 12),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white70,
                      side: const BorderSide(color: Color(0xFF475569)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      padding: const EdgeInsets.symmetric(vertical: 13),
                    ),
                    child: const Text('Đóng'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: selectedOptionKey != null
                        ? () {
                            Navigator.pop(context);
                            widget.onResolve(selectedOptionKey!, notesController.text);
                          }
                        : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      padding: const EdgeInsets.symmetric(vertical: 13),
                    ),
                    child: const Text('Chốt Quyết định', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }
}
