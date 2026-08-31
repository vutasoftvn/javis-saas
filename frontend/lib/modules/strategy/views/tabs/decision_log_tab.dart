import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';
import '../../../../modules/vault/services/evidence_service.dart';
import '../../../../modules/strategy/services/strategy_service.dart';
import '../../../../core/theme/app_theme.dart';

class DecisionLogTab extends StatefulWidget {
  const DecisionLogTab({super.key});

  @override
  State<DecisionLogTab> createState() => _DecisionLogTabState();
}

class _DecisionLogTabState extends State<DecisionLogTab> {
  final _evidenceService = EvidenceService();
  final _strategyService = StrategyService();
  final TextEditingController _searchCtrl = TextEditingController();

  List<Map<String, dynamic>> _projects = [];
  int? _selectedProjectId;
  List<StrategicDecisionModel> _decisions = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String? _projectsError;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final result = await _strategyService.getProjects();
      _projects = result.items;
      _projectsError = result.errorMessage;
      if (_projects.isNotEmpty) {
        final firstId = int.tryParse(_projects.first['id']?.toString() ?? '') ?? 1;
        _selectedProjectId = firstId;
        await _loadDecisions(firstId);
      }
    } catch (e) {
      debugPrint('[DecisionLogTab] _loadInitialData error: $e');
      _projectsError = 'Không thể tải danh sách dự án: $e';
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadDecisions(int projectId) async {
    try {
      final list = await _evidenceService.getDecisions(projectId: projectId);
      if (mounted) {
        setState(() {
          _decisions = list;
        });
      }
    } catch (e) {
      debugPrint('[DecisionLogTab] _loadDecisions error: $e');
    }
  }

  void _onProjectChanged(int? projectId) {
    if (projectId == null) return;
    setState(() => _selectedProjectId = projectId);
    _loadDecisions(projectId);
  }

  void _showRecordDecisionDialog() {
    final questionCtrl = TextEditingController();
    final decisionCtrl = TextEditingController();
    final selectedOptionCtrl = TextEditingController();
    final alternativesCtrl = TextEditingController();
    final rationaleCtrl = TextEditingController();
    String impactLevel = 'MEDIUM';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text('Ghi Nhận Quyết Định Chiến Lược (Decision Log)', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: questionCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Câu hỏi / Vấn đề chiến lược', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: decisionCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Quyết định chốt (*)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: selectedOptionCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Phương án đã chọn', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: alternativesCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Các phương án bị loại bỏ (cách nhau bởi dấu phẩy)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: rationaleCtrl,
                  maxLines: 2,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Lý do căn cứ (Rationale)', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: impactLevel,
                  dropdownColor: const Color(0xFF0F172A),
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(labelText: 'Mức độ tác động', labelStyle: TextStyle(color: AppTheme.textMutedDark)),
                  items: const [
                    DropdownMenuItem(value: 'LOW', child: Text('Thấp (Low)')),
                    DropdownMenuItem(value: 'MEDIUM', child: Text('Trung bình (Medium)')),
                    DropdownMenuItem(value: 'HIGH', child: Text('Cao (High)')),
                    DropdownMenuItem(value: 'PIVOTAL', child: Text('Sống còn (Pivotal)')),
                  ],
                  onChanged: (val) => setDialogState(() => impactLevel = val ?? 'MEDIUM'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark))),
            ElevatedButton(
              onPressed: () async {
                if (decisionCtrl.text.trim().isEmpty || _selectedProjectId == null) return;
                Navigator.pop(ctx);
                final altList = alternativesCtrl.text.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
                await _evidenceService.recordDecision({
                  'project_id': _selectedProjectId!,
                  'question': questionCtrl.text.trim(),
                  'decision': decisionCtrl.text.trim(),
                  'selected_option': selectedOptionCtrl.text.trim(),
                  'alternatives': altList,
                  'rationale': rationaleCtrl.text.trim(),
                  'stage': 'P1_PROBLEM_VALIDATION',
                });
                _loadDecisions(_selectedProjectId!);
              },
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF818CF8), foregroundColor: Colors.black),
              child: const Text('Lưu Quyết Định'),
            ),
          ],
        ),
      ),
    );
  }

  // Danh sách dự án tải thất bại (401/403/409/5xx, JSON hỏng, mất mạng...)
  // trước đây bị nuốt thành `[]` và tab hiển thị y hệt "chưa có dự án nào" —
  // giờ hiện banner lỗi kèm nút thử lại để không đánh lừa người dùng.
  Widget _buildProjectsErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEF4444).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: Color(0xFFEF4444), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Không tải được danh sách dự án: $_projectsError',
              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
            ),
          ),
          TextButton(
            onPressed: _loadInitialData,
            child: const Text('Thử lại'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }

    final filteredDecisions = _decisions.where((d) {
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      final questionMatch = (d.question ?? '').toLowerCase().contains(q);
      final decisionMatch = d.decision.toLowerCase().contains(q);
      final rationaleMatch = (d.rationale ?? '').toLowerCase().contains(q);
      return questionMatch || decisionMatch || rationaleMatch;
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_projectsError != null) _buildProjectsErrorBanner(),
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
                    icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF818CF8), size: 20),
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

              // Search Bar
              Expanded(
                child: Container(
                  height: 38,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.borderDark),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.search, color: AppTheme.textMutedDark, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _searchCtrl,
                          style: const TextStyle(color: Colors.white, fontSize: 13),
                          decoration: const InputDecoration(
                            hintText: 'Tìm kiếm trí nhớ doanh nghiệp (Company Memory)...',
                            hintStyle: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                            border: InputBorder.none,
                            isDense: true,
                          ),
                          onChanged: (val) => setState(() => _searchQuery = val.trim()),
                        ),
                      ),
                      if (_searchQuery.isNotEmpty)
                        GestureDetector(
                          onTap: () {
                            _searchCtrl.clear();
                            setState(() => _searchQuery = '');
                          },
                          child: const Icon(Icons.close, color: AppTheme.textMutedDark, size: 16),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 14),

              ElevatedButton.icon(
                onPressed: _showRecordDecisionDialog,
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Ghi Quyết Định Mới'),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF818CF8), foregroundColor: Colors.black),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Decision Cards List
        Expanded(
          child: filteredDecisions.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.history_edu_outlined, size: 48, color: AppTheme.textMutedDark),
                      const SizedBox(height: 12),
                      const Text('Chưa có quyết định nào được ghi nhận cho dự án này.', style: TextStyle(color: Colors.white70)),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: _showRecordDecisionDialog,
                        icon: const Icon(Icons.add),
                        label: const Text('Ghi Nhận Quyết Định Đầu Tiên'),
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF818CF8), foregroundColor: Colors.black),
                      ),
                    ],
                  ),
                )
              : ListView.separated(
                  itemCount: filteredDecisions.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final d = filteredDecisions[index];
                    final dateStr = '${d.createdAt.day}/${d.createdAt.month}/${d.createdAt.year}';

                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.borderDark),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF818CF8).withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: const Color(0xFF818CF8).withValues(alpha: 0.4)),
                                ),
                                child: Text(
                                  d.status.toUpperCase(),
                                  style: const TextStyle(color: Color(0xFF818CF8), fontSize: 11, fontWeight: FontWeight.bold),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  d.question ?? d.decision,
                                  style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                                ),
                              ),
                              Text(
                                dateStr,
                                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),

                          // Decision chốt
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0F172A),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.check_circle, color: Color(0xFF10B981), size: 16),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'Quyết định: ${d.decision}',
                                    style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 13),
                                  ),
                                ),
                              ],
                            ),
                          ),

                          if (d.selectedOption != null && d.selectedOption!.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text('Phương án chọn: ${d.selectedOption!}', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                          ],

                          if (d.rationale != null && d.rationale!.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text('Căn cứ: ${d.rationale!}', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                          ],

                          if (d.alternatives.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text('Phương án loại: ${d.alternatives.join(", ")}', style: const TextStyle(color: Color(0xFF64748B), fontSize: 12)),
                          ],
                        ],
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}
