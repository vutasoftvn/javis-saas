import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';
import 'hypothesis_card.dart';
import 'evidence_item_card.dart';
import 'assumption_risk_matrix_widget.dart';

class EvidenceBackboneDrawer extends StatefulWidget {
  final int projectId;
  final List<HypothesisModel> hypotheses;
  final List<EvidenceModel> evidences;
  final AssumptionMatrixModel? matrix;
  final Function(Map<String, dynamic>) onCreateHypothesis;
  final Function(Map<String, dynamic>) onAddEvidence;

  const EvidenceBackboneDrawer({
    super.key,
    required this.projectId,
    required this.hypotheses,
    required this.evidences,
    this.matrix,
    required this.onCreateHypothesis,
    required this.onAddEvidence,
  });

  static void show(
    BuildContext context, {
    required int projectId,
    required List<HypothesisModel> hypotheses,
    required List<EvidenceModel> evidences,
    AssumptionMatrixModel? matrix,
    required Function(Map<String, dynamic>) onCreateHypothesis,
    required Function(Map<String, dynamic>) onAddEvidence,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => FractionallySizedBox(
        heightFactor: 0.88,
        child: EvidenceBackboneDrawer(
          projectId: projectId,
          hypotheses: hypotheses,
          evidences: evidences,
          matrix: matrix,
          onCreateHypothesis: onCreateHypothesis,
          onAddEvidence: onAddEvidence,
        ),
      ),
    );
  }

  @override
  State<EvidenceBackboneDrawer> createState() => _EvidenceBackboneDrawerState();
}

class _EvidenceBackboneDrawerState extends State<EvidenceBackboneDrawer>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _showCreateHypothesisDialog() {
    final statementCtrl = TextEditingController();
    String selectedCat = 'problem';
    double importance = 0.8;
    double uncertainty = 0.7;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Thêm Giả Định Cốt Lõi Mới', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Phân loại giả định:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 4),
                DropdownButton<String>(
                  value: selectedCat,
                  dropdownColor: const Color(0xFF1E293B),
                  isExpanded: true,
                  items: [
                    'customer', 'problem', 'solution', 'pricing', 'channel',
                    'revenue', 'cost', 'technology', 'legal', 'operational'
                  ].map((c) => DropdownMenuItem(value: c, child: Text(c.toUpperCase(), style: const TextStyle(color: Colors.white)))).toList(),
                  onChanged: (val) => setDlgState(() => selectedCat = val ?? 'problem'),
                ),
                const SizedBox(height: 12),
                const Text('Nội dung phát biểu giả định:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 4),
                TextField(
                  controller: statementCtrl,
                  maxLines: 3,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: Khách hàng sẵn sàng trả 200k/tháng...',
                    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                    filled: true,
                    fillColor: Colors.white.withValues(alpha: 0.06),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Tầm quan trọng: ${(importance * 100).toInt()}%', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                  ],
                ),
                Slider(
                  value: importance,
                  min: 0.0,
                  max: 1.0,
                  activeColor: const Color(0xFF38BDF8),
                  onChanged: (val) => setDlgState(() => importance = val),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Độ bất định / Chưa rõ: ${(uncertainty * 100).toInt()}%', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                  ],
                ),
                Slider(
                  value: uncertainty,
                  min: 0.0,
                  max: 1.0,
                  activeColor: const Color(0xFFF59E0B),
                  onChanged: (val) => setDlgState(() => uncertainty = val),
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
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF38BDF8), foregroundColor: Colors.black),
              onPressed: () {
                if (statementCtrl.text.trim().isNotEmpty) {
                  widget.onCreateHypothesis({
                    'project_id': widget.projectId,
                    'category': selectedCat,
                    'statement': statementCtrl.text.trim(),
                    'importance': importance,
                    'uncertainty': uncertainty,
                  });
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Lưu Giả Định', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  void _showAddEvidenceDialog(HypothesisModel hypothesis) {
    final claimCtrl = TextEditingController();
    final sourceCtrl = TextEditingController();
    String ladderLevel = 'E1_STATED_INTEREST';
    String direction = 'supports';
    String strength = 'medium';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Ghi Nhận Bằng Chứng Thực Tế', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Giả định: "${hypothesis.statement}"', style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontStyle: FontStyle.italic)),
                const SizedBox(height: 12),
                const Text('Nấc thang Bằng chứng (Evidence Ladder):', style: TextStyle(color: Colors.white70, fontSize: 12)),
                DropdownButton<String>(
                  value: ladderLevel,
                  dropdownColor: const Color(0xFF1E293B),
                  isExpanded: true,
                  items: [
                    'E0_OPINION', 'E1_STATED_INTEREST', 'E2_OBSERVED_PROBLEM',
                    'E3_BEHAVIORAL_COMMITMENT', 'E4_ECONOMIC_COMMITMENT',
                    'E5_REPEAT_BEHAVIOR', 'E6_SCALABLE_EVIDENCE'
                  ].map((lvl) {
                    final lEnum = EvidenceLadderLevel.fromString(lvl);
                    return DropdownMenuItem(value: lvl, child: Text('${lEnum.code}: ${lEnum.shortLabelVi} (w: ${lEnum.weight})', style: TextStyle(color: lEnum.color, fontWeight: FontWeight.bold)));
                  }).toList(),
                  onChanged: (val) => setDlgState(() => ladderLevel = val ?? 'E1_STATED_INTEREST'),
                ),
                const SizedBox(height: 10),
                const Text('Bằng chứng chứng minh hoặc bác bỏ điều gì:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                TextField(
                  controller: claimCtrl,
                  maxLines: 2,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: Khách hàng đã chuyển cọc 1 triệu...',
                    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                    filled: true,
                    fillColor: Colors.white.withValues(alpha: 0.06),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
                const SizedBox(height: 10),
                const Text('Nguồn gốc bằng chứng:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                TextField(
                  controller: sourceCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: Phỏng vấn CEO công ty X, Link Stripe Invoice...',
                    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                    filled: true,
                    fillColor: Colors.white.withValues(alpha: 0.06),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Hướng tác động:', style: TextStyle(color: Colors.white70, fontSize: 11)),
                          DropdownButton<String>(
                            value: direction,
                            dropdownColor: const Color(0xFF1E293B),
                            isExpanded: true,
                            items: const [
                              DropdownMenuItem(value: 'supports', child: Text('Ủng hộ (+)', style: TextStyle(color: Color(0xFF10B981)))),
                              DropdownMenuItem(value: 'contradicts', child: Text('Phủ định (-)', style: TextStyle(color: Color(0xFFEF4444)))),
                            ],
                            onChanged: (val) => setDlgState(() => direction = val ?? 'supports'),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Độ mạnh:', style: TextStyle(color: Colors.white70, fontSize: 11)),
                          DropdownButton<String>(
                            value: strength,
                            dropdownColor: const Color(0xFF1E293B),
                            isExpanded: true,
                            items: const [
                              DropdownMenuItem(value: 'weak', child: Text('Yếu', style: TextStyle(color: Colors.white70))),
                              DropdownMenuItem(value: 'medium', child: Text('Vừa', style: TextStyle(color: Colors.white))),
                              DropdownMenuItem(value: 'strong', child: Text('Mạnh', style: TextStyle(color: Colors.amber))),
                            ],
                            onChanged: (val) => setDlgState(() => strength = val ?? 'medium'),
                          ),
                        ],
                      ),
                    ),
                  ],
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
                if (claimCtrl.text.trim().isNotEmpty && sourceCtrl.text.trim().isNotEmpty) {
                  widget.onAddEvidence({
                    'project_id': widget.projectId,
                    'type': 'interview',
                    'ladder_level': ladderLevel,
                    'claim_supported': claimCtrl.text.trim(),
                    'source': sourceCtrl.text.trim(),
                    'direction': direction,
                    'strength': strength,
                    'hypothesis_refs': [hypothesis.id],
                  });
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Lưu Bằng Chứng', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF0B1120),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(top: BorderSide(color: Color(0xFF334155), width: 1.5)),
      ),
      child: Column(
        children: [
          // Header handle & title
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 10),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.hub_outlined, color: Color(0xFF38BDF8), size: 20),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'TRỤC XƯƠNG SỐNG KIỂM CHỨNG (ASSUMPTION BACKBONE)',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'Quản lý Giả định, Thang bằng chứng (E0-E6) & Ma trận rủi ro',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF38BDF8),
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('+ Giả Định', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                  onPressed: _showCreateHypothesisDialog,
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          // Tab Bar
          TabBar(
            controller: _tabController,
            indicatorColor: const Color(0xFF38BDF8),
            labelColor: const Color(0xFF38BDF8),
            unselectedLabelColor: Colors.white54,
            tabs: [
              Tab(text: 'Giả Định (${widget.hypotheses.length})'),
              const Tab(text: 'Ma Trận Rủi Ro (2x2)'),
              Tab(text: 'Kho Bằng Chứng (${widget.evidences.length})'),
            ],
          ),
          const SizedBox(height: 10),

          // Tab Views
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: TabBarView(
                controller: _tabController,
                children: [
                  // Tab 1: Hypotheses Backlog
                  widget.hypotheses.isEmpty
                      ? Center(
                          child: Text(
                            'Chưa có giả định nào. Bấm "+ Giả Định" để thêm mới!',
                            style: TextStyle(color: Colors.white.withValues(alpha: 0.4)),
                          ),
                        )
                      : ListView.builder(
                          itemCount: widget.hypotheses.length,
                          itemBuilder: (ctx, i) {
                            final h = widget.hypotheses[i];
                            return HypothesisCard(
                              hypothesis: h,
                              onAddEvidence: () => _showAddEvidenceDialog(h),
                            );
                          },
                        ),

                  // Tab 2: Risk Matrix 2x2
                  widget.matrix == null
                      ? const Center(child: CircularProgressIndicator())
                      : AssumptionRiskMatrixWidget(
                          matrix: widget.matrix!,
                          onAddEvidence: (h) => _showAddEvidenceDialog(h),
                        ),

                  // Tab 3: Evidence Vault
                  widget.evidences.isEmpty
                      ? Center(
                          child: Text(
                            'Chưa có bằng chứng nào được ghi nhận.',
                            style: TextStyle(color: Colors.white.withValues(alpha: 0.4)),
                          ),
                        )
                      : ListView.builder(
                          itemCount: widget.evidences.length,
                          itemBuilder: (ctx, i) => EvidenceItemCard(evidence: widget.evidences[i]),
                        ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
