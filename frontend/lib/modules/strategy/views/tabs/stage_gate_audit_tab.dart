import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/stage_gate_model.dart';
import '../../../../data/models/stage_model.dart';
import '../../../../modules/strategy/services/stage_gate_service.dart';
import '../../../../modules/strategy/services/strategy_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/stage_badge.dart';

class StageGateAuditTab extends StatefulWidget {
  const StageGateAuditTab({super.key});

  @override
  State<StageGateAuditTab> createState() => _StageGateAuditTabState();
}

class _StageGateAuditTabState extends State<StageGateAuditTab> {
  final _stageGateService = StageGateService();
  final _strategyService = StrategyService();

  List<Map<String, dynamic>> _projects = [];
  int? _selectedProjectId;
  ProjectStage _currentStage = ProjectStage.s1ProblemValidation;
  StageGateAuditModel? _audit;
  bool _isLoading = true;
  bool _isAuditing = false;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final projects = await _strategyService.getProjects();
      _projects = projects.cast<Map<String, dynamic>>();
      if (_projects.isNotEmpty) {
        final firstId = int.tryParse(_projects.first['id']?.toString() ?? '') ?? 1;
        _selectedProjectId = firstId;
        final rawStage = _projects.first['project_stage']?.toString();
        _currentStage = ProjectStage.fromString(rawStage);
        await _loadAuditData(firstId);
      }
    } catch (e) {
      debugPrint('[StageGateAuditTab] _loadInitialData error: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadAuditData(int projectId) async {
    try {
      final history = await _stageGateService.getAuditHistory(projectId);
      if (mounted) {
        setState(() {
          _audit = history.isNotEmpty ? history.first : null;
        });
      }
    } catch (e) {
      debugPrint('[StageGateAuditTab] _loadAuditData error: $e');
    }
  }

  void _onProjectChanged(int? projectId) {
    if (projectId == null) return;
    final proj = _projects.firstWhereOrNull((p) => (int.tryParse(p['id']?.toString() ?? '') ?? 0) == projectId);
    setState(() {
      _selectedProjectId = projectId;
      if (proj != null) {
        _currentStage = ProjectStage.fromString(proj['project_stage']?.toString());
      }
    });
    _loadAuditData(projectId);
  }

  Future<void> _runAudit() async {
    if (_selectedProjectId == null) return;
    setState(() => _isAuditing = true);
    try {
      final audit = await _stageGateService.auditStageReadiness(projectId: _selectedProjectId!);
      if (mounted) {
        setState(() {
          _audit = audit;
        });
      }
    } catch (e) {
      debugPrint('[StageGateAuditTab] _runAudit error: $e');
    } finally {
      if (mounted) setState(() => _isAuditing = false);
    }
  }

  Future<void> _applyTransition(int auditId) async {
    if (_selectedProjectId == null) return;
    try {
      final success = await _stageGateService.applyStageTransition(auditId: auditId);
      if (success) {
        Get.snackbar(
          'Thành Công',
          'Đã chuyển Stage dự án thành công!',
          backgroundColor: const Color(0xFF10B981),
          colorText: Colors.black,
          margin: const EdgeInsets.all(16),
        );
        await _loadInitialData();
      }
    } catch (e) {
      debugPrint('[StageGateAuditTab] _applyTransition error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }

    final audit = _audit;
    final isReady = audit != null && audit.auditStatus == AuditStatus.approved;
    final allCriteria = audit != null ? [...audit.passedCriteria, ...audit.missingCriteria] : <StageGateCriteriaModel>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
                    icon: const Icon(Icons.arrow_drop_down, color: Color(0xFFF59E0B), size: 20),
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
              const SizedBox(width: 12),
              StageBadge(stage: _currentStage),
              const Spacer(),
              ElevatedButton.icon(
                onPressed: _isAuditing ? null : _runAudit,
                icon: _isAuditing
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.verified_user_outlined, size: 16),
                label: Text(_isAuditing ? 'Đang Thẩm Định...' : 'Chạy Thẩm Định Stage-Gate'),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFF59E0B), foregroundColor: Colors.black),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Body Content
        Expanded(
          child: audit == null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.fact_check_outlined, size: 48, color: AppTheme.textMutedDark),
                      const SizedBox(height: 12),
                      const Text('Chưa có kết quả thẩm định Stage-Gate cho dự án này.', style: TextStyle(color: Colors.white70)),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: _runAudit,
                        icon: const Icon(Icons.play_arrow),
                        label: const Text('Chạy Thẩm Định Ngay'),
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFF59E0B), foregroundColor: Colors.black),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Readiness Score Card
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceDark,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: isReady ? const Color(0xFF10B981) : const Color(0xFFEF4444)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 64,
                              height: 64,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: (isReady ? const Color(0xFF10B981) : const Color(0xFFEF4444)).withValues(alpha: 0.15),
                                border: Border.all(
                                  color: isReady ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                  width: 2,
                                ),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                '${audit.readinessScore.toInt()}%',
                                style: TextStyle(
                                  color: isReady ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    isReady ? 'ĐỦ ĐIỀU KIỆN CHUYỂN STAGE' : 'CHƯA ĐỦ ĐIỀU KIỆN CHUYỂN STAGE',
                                    style: TextStyle(
                                      color: isReady ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    audit.recommendationNote.isNotEmpty
                                        ? audit.recommendationNote
                                        : 'Đánh giá hoàn thành cho Stage ${audit.fromStage} -> ${audit.toStage}.',
                                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                                  ),
                                ],
                              ),
                            ),
                            if (isReady)
                              ElevatedButton(
                                onPressed: () => _applyTransition(audit.id),
                                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981), foregroundColor: Colors.black),
                                child: const Text('Chuyển Sang Stage Kế Tiếp'),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Checklist Items
                      const Text('Danh Mục Tiêu Chí Cổng Stage (Gate Criteria)', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 10),
                      ...allCriteria.map((item) {
                        final passed = item.isMet;
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceDark,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: passed ? const Color(0xFF10B981).withValues(alpha: 0.3) : const Color(0xFFEF4444).withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                passed ? Icons.check_circle : Icons.cancel_outlined,
                                color: passed ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                size: 20,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(item.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13)),
                                    if (item.description.isNotEmpty)
                                      Text(item.description, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
        ),
      ],
    );
  }
}
