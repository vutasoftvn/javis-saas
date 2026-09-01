import 'package:flutter/material.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../../../modules/agents/services/agent_platform_service.dart';

class DecisionRecordsDialog extends StatefulWidget {
  const DecisionRecordsDialog({super.key});

  @override
  State<DecisionRecordsDialog> createState() => _DecisionRecordsDialogState();
}

class _DecisionRecordsDialogState extends State<DecisionRecordsDialog> {
  final AgentPlatformService _service = AgentPlatformService();
  bool _isLoading = true;
  List<Map<String, dynamic>> _decisions = [];

  @override
  void initState() {
    super.initState();
    _loadDecisions();
  }

  Future<void> _loadDecisions() async {
    setState(() => _isLoading = true);
    final list = await _service.listDecisions();
    setState(() {
      _decisions = list;
      _isLoading = false;
    });
  }

  Future<void> _acceptDecision(int id) async {
    final res = await _service.acceptDecision(id);
    if (mounted && res != null) {
      AppToast.success('Đã phê duyệt quyết định kiến trúc (ADR)!');
      _loadDecisions();
    }
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
                    color: Colors.cyanAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.bookmark_border_rounded, color: Colors.cyanAccent, size: 22),
                ),
                const SizedBox(width: 14),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Architectural & Strategic Decision Records (ADR)',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                      Text(
                        'Sổ ghi nhận quyết định kiến trúc, tác động và phương án cân nhắc của Agent Workforce',
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
                  ? const Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
                  : _decisions.isEmpty
                      ? Center(
                          child: Text('Chưa có bản ghi quyết định ADR nào.', style: TextStyle(color: Colors.grey.shade500)),
                        )
                      : ListView.separated(
                          itemCount: _decisions.length,
                          separatorBuilder: (context, index) => const SizedBox(height: 12),
                          itemBuilder: (ctx, i) {
                            final dr = _decisions[i];
                            final id = dr['id'] is int ? dr['id'] as int : int.tryParse(dr['id'].toString()) ?? 0;
                            final title = dr['title'] ?? 'ADR Title';
                            final status = (dr['status'] ?? 'PROPOSED').toString().toUpperCase();
                            final author = dr['author_agent_key'] ?? 'Agent';
                            final contextSummary = dr['context_summary'] ?? '';
                            final decisionContent = dr['decision_content'] ?? '';
                            final consequences = dr['consequences'] ?? '';
                            final alternatives = dr['alternatives_considered'] ?? '';

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
                                  const SizedBox(height: 4),
                                  Text('Tác giả: $author', style: TextStyle(color: Colors.grey.shade400, fontSize: 12)),
                                  const SizedBox(height: 10),
                                  _buildSection('Bối cảnh (Context)', contextSummary),
                                  const SizedBox(height: 8),
                                  _buildSection('Quyết định (Decision)', decisionContent, isHighlight: true),
                                  if (consequences.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    _buildSection('Hệ quả & Tác động (Consequences)', consequences),
                                  ],
                                  if (alternatives.isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    _buildSection('Phương án cân nhắc khác (Alternatives)', alternatives),
                                  ],
                                  if (!isAccepted) ...[
                                    const Divider(color: Color(0xFF334155), height: 16),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.end,
                                      children: [
                                        ElevatedButton(
                                          onPressed: () => _acceptDecision(id),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: const Color(0xFF10B981),
                                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                          ),
                                          child: const Text('Phê duyệt Quyết định', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
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

  Widget _buildSection(String label, String content, {bool isHighlight = false}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: isHighlight ? Colors.cyanAccent.withValues(alpha: 0.08) : const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isHighlight ? Colors.cyanAccent.withValues(alpha: 0.3) : const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: isHighlight ? Colors.cyanAccent : Colors.grey.shade400, fontSize: 11, fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Text(content, style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 12.5, height: 1.4)),
        ],
      ),
    );
  }
}
