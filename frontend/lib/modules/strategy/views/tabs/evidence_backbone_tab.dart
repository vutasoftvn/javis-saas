import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../data/services/evidence_service.dart';
import '../../../../data/services/strategy_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../hologram_hub/widgets/evidence/assumption_risk_matrix_widget.dart';
import '../../../hologram_hub/widgets/evidence/hypothesis_card.dart';
import '../../../hologram_hub/widgets/evidence/evidence_item_card.dart';

class EvidenceBackboneTab extends StatefulWidget {
  const EvidenceBackboneTab({super.key});

  @override
  State<EvidenceBackboneTab> createState() => _EvidenceBackboneTabState();
}

class _EvidenceBackboneTabState extends State<EvidenceBackboneTab> with SingleTickerProviderStateMixin {
  final _evidenceService = EvidenceService();
  final _strategyService = StrategyService();
  late TabController _tabController;

  List<Map<String, dynamic>> _projects = [];
  int? _selectedProjectId;
  List<HypothesisModel> _hypotheses = [];
  List<EvidenceModel> _evidences = [];
  AssumptionMatrixModel? _matrix;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadInitialData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final projects = await _strategyService.getProjects();
      _projects = projects.cast<Map<String, dynamic>>();
      if (_projects.isNotEmpty) {
        final firstId = int.tryParse(_projects.first['id']?.toString() ?? '') ?? 1;
        _selectedProjectId = firstId;
        await _loadEvidenceData(firstId);
      }
    } catch (e) {
      debugPrint('[EvidenceBackboneTab] _loadInitialData error: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadEvidenceData(int projectId) async {
    try {
      final hypos = await _evidenceService.getHypotheses(projectId: projectId);
      final evs = await _evidenceService.getEvidences(projectId: projectId);
      final matrix = await _evidenceService.getAssumptionMatrix(projectId);
      if (mounted) {
        setState(() {
          _hypotheses = hypos;
          _evidences = evs;
          _matrix = matrix;
        });
      }
    } catch (e) {
      debugPrint('[EvidenceBackboneTab] _loadEvidenceData error: $e');
    }
  }

  void _onProjectChanged(int? projectId) {
    if (projectId == null) return;
    setState(() => _selectedProjectId = projectId);
    _loadEvidenceData(projectId);
  }

  void _showAddHypothesisDialog() {
    final statementCtrl = TextEditingController();
    final falsificationCtrl = TextEditingController();
    String category = 'customer_problem';
    double importance = 0.8;
    double uncertainty = 0.7;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Tạo Giả Định Chiến Lược (Hypothesis)', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: category,
                  dropdownColor: const Color(0xFF0F172A),
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Phân loại', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                  items: const [
                    DropdownMenuItem(value: 'customer_problem', child: Text('Vấn đề khách hàng')),
                    DropdownMenuItem(value: 'value_proposition', child: Text('Đề xuất giá trị')),
                    DropdownMenuItem(value: 'willingness_to_pay', child: Text('Sẵn sàng chi trả')),
                    DropdownMenuItem(value: 'channel_viability', child: Text('Kênh phân phối')),
                    DropdownMenuItem(value: 'unit_economics', child: Text('Kinh tế đơn vị')),
                  ],
                  onChanged: (val) => setDialogState(() => category = val ?? 'customer_problem'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: statementCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Nội dung giả định (*)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: falsificationCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Điều kiện bác bỏ (Falsification)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('Tầm quan trọng: ', style: TextStyle(color: Colors.white70)),
                    Text('${(importance * 100).toInt()}%', style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold)),
                  ],
                ),
                Slider(
                  value: importance,
                  onChanged: (v) => setDialogState(() => importance = v),
                  activeColor: AppTheme.primary,
                ),
                Row(
                  children: [
                    const Text('Độ bất định: ', style: TextStyle(color: Colors.white70)),
                    Text('${(uncertainty * 100).toInt()}%', style: const TextStyle(color: Color(0xFFEF4444), fontWeight: FontWeight.bold)),
                  ],
                ),
                Slider(
                  value: uncertainty,
                  onChanged: (v) => setDialogState(() => uncertainty = v),
                  activeColor: const Color(0xFFEF4444),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark))),
            ElevatedButton(
              onPressed: () async {
                if (statementCtrl.text.trim().isEmpty || _selectedProjectId == null) return;
                Navigator.pop(ctx);
                await _evidenceService.createHypothesis({
                  'project_id': _selectedProjectId!,
                  'statement': statementCtrl.text.trim(),
                  'falsification_condition': falsificationCtrl.text.trim(),
                  'category': category,
                  'importance': importance,
                  'uncertainty': uncertainty,
                });
                _loadEvidenceData(_selectedProjectId!);
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: Colors.black),
              child: const Text('Lưu Giả Định'),
            ),
          ],
        ),
      ),
    );
  }

  void _showAddEvidenceDialog() {
    final claimCtrl = TextEditingController();
    final sourceCtrl = TextEditingController();
    String ladderLevel = 'E1_STATED_INTEREST';
    String type = 'interview';
    String direction = 'supports';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Bổ Sung Bằng Chứng Thực Địa', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: ladderLevel,
                  dropdownColor: const Color(0xFF0F172A),
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Cấp độ Bằng chứng (Evidence Ladder)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                  items: const [
                    DropdownMenuItem(value: 'E0_OPINION', child: Text('E0 - Ý kiến cá nhân (0.1)')),
                    DropdownMenuItem(value: 'E1_STATED_INTEREST', child: Text('E1 - Khách nói quan tâm (0.2)')),
                    DropdownMenuItem(value: 'E2_OBSERVED_PROBLEM', child: Text('E2 - Quan sát thực tế (0.4)')),
                    DropdownMenuItem(value: 'E3_BEHAVIORAL_COMMITMENT', child: Text('E3 - Cam kết hành vi / Thời gian (0.6)')),
                    DropdownMenuItem(value: 'E4_ECONOMIC_COMMITMENT', child: Text('E4 - Đặt cọc / Trả tiền (0.85)')),
                    DropdownMenuItem(value: 'E5_REPEAT_BEHAVIOR', child: Text('E5 - Tái mua / Sử dụng lặp lại (0.95)')),
                  ],
                  onChanged: (val) => setDialogState(() => ladderLevel = val ?? 'E1_STATED_INTEREST'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: claimCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Tuyên bố được chứng minh (*)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: sourceCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Nguồn bằng chứng (File/Link/Cuộc gọi)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: direction,
                  dropdownColor: const Color(0xFF0F172A),
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Chiều tác động', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                  items: const [
                    DropdownMenuItem(value: 'supports', child: Text('Ủng hộ giả định (+)')),
                    DropdownMenuItem(value: 'contradicts', child: Text('Phản bác giả định (-)')),
                  ],
                  onChanged: (val) => setDialogState(() => direction = val ?? 'supports'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark))),
            ElevatedButton(
              onPressed: () async {
                if (claimCtrl.text.trim().isEmpty || _selectedProjectId == null) return;
                Navigator.pop(ctx);
                await _evidenceService.createEvidence({
                  'project_id': _selectedProjectId!,
                  'claim_supported': claimCtrl.text.trim(),
                  'source': sourceCtrl.text.trim(),
                  'ladder_level': ladderLevel,
                  'type': type,
                  'direction': direction,
                });
                _loadEvidenceData(_selectedProjectId!);
              },
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF38BDF8), foregroundColor: Colors.black),
              child: const Text('Lưu Bằng Chứng'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Top Toolbar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.borderDark),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<int>(
                    value: _selectedProjectId,
                    hint: const Text('Chọn Dự Án...', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                    dropdownColor: const Color(0xFF0F172A),
                    icon: const Icon(Icons.arrow_drop_down, color: AppTheme.primary, size: 20),
                    items: _projects.map((p) {
                      final id = int.tryParse(p['id']?.toString() ?? '') ?? 0;
                      final title = p['title'] ?? 'Dự án $id';
                      return DropdownMenuItem<int>(
                        value: id,
                        child: Text(title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                      );
                    }).toList(),
                    onChanged: _onProjectChanged,
                  ),
                ),
              ),
              const SizedBox(width: 14),

              ElevatedButton.icon(
                onPressed: _showAddHypothesisDialog,
                icon: const Icon(Icons.add_circle_outline, size: 16),
                label: const Text('Thêm Giả Định'),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: Colors.black),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: _showAddEvidenceDialog,
                icon: const Icon(Icons.assignment_turned_in_outlined, size: 16),
                label: const Text('Thêm Bằng Chứng'),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF38BDF8), foregroundColor: Colors.black),
              ),

              const Spacer(),

              SizedBox(
                width: 380,
                child: TabBar(
                  controller: _tabController,
                  indicatorColor: AppTheme.primary,
                  indicatorWeight: 3,
                  labelColor: AppTheme.primary,
                  unselectedLabelColor: AppTheme.textMutedDark,
                  labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  tabs: const [
                    Tab(text: 'Ma Trận Rủi Ro (2x2)'),
                    Tab(text: 'Danh Sách Giả Định'),
                    Tab(text: 'Bằng Chứng Thực Địa'),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Tabs Body
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              // 1. Assumption Risk Matrix
              _matrix != null
                  ? AssumptionRiskMatrixWidget(
                      matrix: _matrix!,
                      onSelectHypothesis: (h) {
                        _tabController.animateTo(1);
                      },
                    )
                  : const Center(child: Text('Chưa có dữ liệu ma trận giả định', style: TextStyle(color: Colors.white70))),

              // 2. Hypotheses List
              _hypotheses.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.lightbulb_outline, size: 48, color: AppTheme.textMutedDark),
                          const SizedBox(height: 12),
                          const Text('Chưa có giả định nào cho dự án này.', style: TextStyle(color: Colors.white70)),
                          const SizedBox(height: 12),
                          ElevatedButton.icon(
                            onPressed: _showAddHypothesisDialog,
                            icon: const Icon(Icons.add),
                            label: const Text('Thêm Giả Định Đầu Tiên'),
                            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: Colors.black),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _hypotheses.length,
                      itemBuilder: (context, index) {
                        final h = _hypotheses[index];
                        return HypothesisCard(
                          hypothesis: h,
                          onAddEvidence: _showAddEvidenceDialog,
                        );
                      },
                    ),

              // 3. Evidence Ladder Items
              _evidences.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.layers_outlined, size: 48, color: AppTheme.textMutedDark),
                          const SizedBox(height: 12),
                          const Text('Chưa có bằng chứng thực địa nào.', style: TextStyle(color: Colors.white70)),
                          const SizedBox(height: 12),
                          ElevatedButton.icon(
                            onPressed: _showAddEvidenceDialog,
                            icon: const Icon(Icons.add),
                            label: const Text('Thu Thập Bằng Chứng Ngay'),
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF38BDF8), foregroundColor: Colors.black),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _evidences.length,
                      itemBuilder: (context, index) {
                        final e = _evidences[index];
                        return EvidenceItemCard(
                          evidence: e,
                        );
                      },
                    ),
            ],
          ),
        ),
      ],
    );
  }
}
