import 'package:flutter/material.dart';
import '../../../../shared/widgets/ai_advisory_disclosure.dart';

class ContractRiskAnalyzerDialog extends StatefulWidget {

  final Future<Map<String, dynamic>?> Function({
    required String contractText,
    String contractType,
  }) onAnalyze;

  const ContractRiskAnalyzerDialog({super.key, required this.onAnalyze});

  @override
  State<ContractRiskAnalyzerDialog> createState() => _ContractRiskAnalyzerDialogState();
}

class _ContractRiskAnalyzerDialogState extends State<ContractRiskAnalyzerDialog> {
  final _textController = TextEditingController();
  String _contractType = 'COMMERCIAL_SERVICE';
  bool _isLoading = false;
  Map<String, dynamic>? _analysisResult;

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _handleAnalyze() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _isLoading = true;
      _analysisResult = null;
    });

    try {
      final res = await widget.onAnalyze(
        contractText: text,
        contractType: _contractType,
      );
      if (mounted) {
        setState(() {
          _analysisResult = res;
        });
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 680, maxHeight: 720),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: const [
                      Icon(Icons.gavel_rounded, color: Color(0xFF00E5FF), size: 22),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'AI CONTRACT RISK ANALYZER',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    isExpanded: true,
                    initialValue: _contractType,
                    dropdownColor: const Color(0xFF131D35),
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      labelText: 'Loại hợp đồng',
                      labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                      filled: true,
                      fillColor: const Color(0xFF131D35),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                    ),

                    items: const [
                      DropdownMenuItem(value: 'COMMERCIAL_SERVICE', child: Text('Hợp đồng Dịch vụ Thương mại / SaaS')),
                      DropdownMenuItem(value: 'EMPLOYMENT', child: Text('Hợp đồng Lao động & Cộng tác viên')),
                      DropdownMenuItem(value: 'NDA', child: Text('Thỏa thuận Bảo mật Thông tin (NDA)')),
                      DropdownMenuItem(value: 'PARTNERSHIP', child: Text('Thỏa thuận Hợp tác Kinh doanh')),
                    ],
                    onChanged: (val) => setState(() => _contractType = val ?? 'COMMERCIAL_SERVICE'),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : _handleAnalyze,
                  icon: _isLoading
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                      : const Icon(Icons.auto_awesome_rounded, size: 16, color: Colors.black),
                  label: const Text('Rà soát AI', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00E5FF),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const AiAdvisoryDisclosure(domain: 'Pháp chế & Hợp đồng'),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _textController,
                      maxLines: 6,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Dán toàn văn hoặc các điều khoản hợp đồng cần rà soát vào đây...\nVí dụ: Điều khoản phạt vi phạm, sở hữu trí tuệ, chấm dứt, thanh toán...',
                        hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF131D35),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                      ),
                    ),
                    if (_analysisResult != null) ...[
                      const SizedBox(height: 18),
                      _buildAnalysisResultView(_analysisResult!),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalysisResultView(Map<String, dynamic> result) {
    final riskLevel = result['risk_level']?.toString() ?? 'THAM KHẢO';
    final risks = (result['risks'] as List<dynamic>?) ?? [];
    final recs = (result['recommendations'] as List<dynamic>?) ?? [];

    Color scoreColor = const Color(0xFF38BDF8);
    if (riskLevel.contains('HIGH') || riskLevel.contains('NGUY HIỂM')) {
      scoreColor = const Color(0xFFEF4444);
    } else if (riskLevel.contains('MEDIUM') || riskLevel.contains('TRUNG BÌNH')) {
      scoreColor = const Color(0xFFF59E0B);
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: scoreColor.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: scoreColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.gavel_rounded, color: scoreColor, size: 16),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'RÀ SOÁT PHÁP LÝ THAM KHẢO ($riskLevel)',
                          style: TextStyle(color: scoreColor, fontWeight: FontWeight.bold, fontSize: 12),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'Phát hiện: ${risks.length} điểm cần lưu ý',
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
              ),
            ],
          ),

          const SizedBox(height: 14),
          if (risks.isNotEmpty) ...[
            const Text(
              'CÁC ĐIỀU KHOẢN RỦI RO PHÁT HIỆN:',
              style: TextStyle(color: Color(0xFFEF4444), fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 0.8),
            ),
            const SizedBox(height: 8),
            ...risks.map((r) {
              final rMap = r as Map<String, dynamic>;
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.25)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            rMap['category']?.toString() ?? 'RISK',
                            style: const TextStyle(color: Color(0xFFEF4444), fontSize: 9, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            rMap['clause_snippet']?.toString() ?? '',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Vấn đề: ${rMap['issue'] ?? ''}',
                      style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 11),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '👉 Khuyến nghị: ${rMap['recommendation'] ?? ''}',
                      style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 11),
                    ),
                  ],
                ),
              );
            }),
          ],
          if (recs.isNotEmpty && risks.isEmpty) ...[
            const SizedBox(height: 8),
            ...recs.map((rc) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 14),
                      const SizedBox(width: 6),
                      Expanded(child: Text('$rc', style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12))),
                    ],
                  ),
                )),
          ],
        ],
      ),
    );
  }
}
