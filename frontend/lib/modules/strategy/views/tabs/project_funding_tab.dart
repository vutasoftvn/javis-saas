import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/floating_app_bar.dart';
import '../../../../modules/finance/services/policy_funding_service.dart';
import '../../controllers/strategy_controller.dart';
import '../../widgets/funding/funding_verification_modals.dart';
import '../../widgets/funding/funding_matches_tab_content.dart';
import '../../widgets/funding/funding_catalog_tab_content.dart';
import '../../widgets/funding/funding_watchlist_tab_content.dart';

class ProjectFundingTab extends StatefulWidget {
  final String? projectId;

  const ProjectFundingTab({super.key, this.projectId});

  @override
  State<ProjectFundingTab> createState() => _ProjectFundingTabState();
}

class _ProjectFundingTabState extends State<ProjectFundingTab> {
  final PolicyFundingService _service = PolicyFundingService();
  StrategyController get strategyController => Get.find<StrategyController>();

  int _activeSubTabIndex = 0; // 0: Matches, 1: Catalog, 2: Watchlist
  List<dynamic> _currentBenefits = [];
  List<dynamic> _draftWatchlist = [];
  bool _isLoadingCatalog = false;
  bool _isLoading = false;
  String? _errorMessage;
  Map<String, dynamic> _overviewData = {};
  String? _currentProjectId;

  @override
  void initState() {
    super.initState();
    _currentProjectId = widget.projectId;
    if (_currentProjectId == null && strategyController.projects.isNotEmpty) {
      _currentProjectId = strategyController.projects.first['id']?.toString();
    }
    if (_currentProjectId != null) {
      _loadOverview();
    }
    _loadCatalogData();
  }

  Future<void> _loadCatalogData() async {
    setState(() => _isLoadingCatalog = true);
    try {
      final benefits = await _service.getCurrentBenefits();
      final drafts = await _service.getDraftWatchlist();
      setState(() {
        _currentBenefits = benefits;
        _draftWatchlist = drafts;
        _isLoadingCatalog = false;
      });
    } catch (_) {
      setState(() => _isLoadingCatalog = false);
    }
  }

  Future<void> _loadOverview() async {
    if (_currentProjectId == null) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final data = await _service.getFundingOverview(_currentProjectId!);
      setState(() {
        _overviewData = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _runMatching() async {
    if (_currentProjectId == null) return;
    setState(() => _isLoading = true);
    try {
      await _service.triggerMatching(_currentProjectId!);
      await _loadOverview();
      await _loadCatalogData();
      Get.snackbar('Thành công', 'Đã hoàn tất khớp nối chính sách cho dự án.', snackPosition: SnackPosition.BOTTOM);
    } catch (e) {
      setState(() => _isLoading = false);
      Get.snackbar('Lỗi', e.toString(), snackPosition: SnackPosition.BOTTOM);
    }
  }

  Future<void> _create12wyTask(int missingReqId, String title) async {
    if (_currentProjectId == null) return;
    try {
      await _service.create12wyTask(projectId: _currentProjectId!, missingRequirementId: missingReqId, customTitle: title);
      await _loadOverview();
      Get.snackbar('Đã tạo nhiệm vụ', 'Nhiệm vụ "$title" đã được thêm vào 12WY.', snackPosition: SnackPosition.BOTTOM);
    } catch (e) {
      Get.snackbar('Lỗi', e.toString(), snackPosition: SnackPosition.BOTTOM);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (strategyController.projects.isEmpty) {
      return Center(
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppTheme.borderDark)),
          child: const Text('Chưa có Dự án nào để phân tích chính sách và nguồn lực.', style: TextStyle(color: Colors.white70)),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          JavisFloatingAppBar(
            title: 'Nguồn lực & Chính sách (Policy/Funding Intelligence)',
            subtitle: 'Phân tích cơ hội quỹ hỗ trợ, voucher, credit hạ tầng và điều kiện hồ sơ gắn với từng Dự án.',
            icon: Icons.account_balance_outlined,
            actions: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(100), border: Border.all(color: AppTheme.borderDark)),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _currentProjectId,
                    dropdownColor: AppTheme.surfaceDark,
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
                    icon: const Icon(Icons.arrow_drop_down, color: AppTheme.primary),
                    items: strategyController.projects.map((p) => DropdownMenuItem<String>(value: p['id']?.toString() ?? '', child: Text(p['title'] ?? 'Dự án'))).toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() => _currentProjectId = val);
                        _loadOverview();
                      }
                    },
                  ),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: _isLoading ? null : _runMatching,
                icon: const Icon(Icons.auto_awesome, size: 16),
                label: const Text('Khớp nối cơ hội (AI Match)'),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100))),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Sub Navigation
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(10), border: Border.all(color: AppTheme.borderDark)),
            child: Row(
              children: [
                _buildSubNavButton(0, 'Khớp nối với Dự án', Icons.track_changes_rounded),
                _buildSubNavButton(1, 'Quyền lợi hiện hành (Catalog 23)', Icons.verified_outlined),
                _buildSubNavButton(2, 'Dự thảo 2026–2035 (Watchlist)', Icons.visibility_outlined),
              ],
            ),
          ),
          const SizedBox(height: 16),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                : _errorMessage != null
                    ? Center(child: Text(_errorMessage!, style: const TextStyle(color: AppTheme.error)))
                    : _activeSubTabIndex == 0
                        ? FundingMatchesTabContent(overviewData: _overviewData, onCreate12wyTask: _create12wyTask)
                        : _activeSubTabIndex == 1
                            ? FundingCatalogTabContent(
                                currentBenefits: _currentBenefits,
                                isLoading: _isLoadingCatalog,
                                onVerifyProgram: (p) => FundingVerificationModals.openFounderVerificationModal(context, _service, p, () async {
                                  await _loadCatalogData();
                                  await _loadOverview();
                                }),
                              )
                            : FundingWatchlistTabContent(draftWatchlist: _draftWatchlist),
          ),
        ],
      ),
    );
  }

  Widget _buildSubNavButton(int index, String label, IconData icon) {
    final isSelected = _activeSubTabIndex == index;
    return Expanded(
      child: InkWell(
        onTap: () {
          setState(() => _activeSubTabIndex = index);
          if (index > 0) _loadCatalogData();
        },
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: isSelected ? AppTheme.primary.withValues(alpha: 0.4) : Colors.transparent),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: isSelected ? AppTheme.primary : AppTheme.textMutedDark, size: 16),
              const SizedBox(width: 8),
              Text(label, style: TextStyle(color: isSelected ? Colors.white : AppTheme.textMutedDark, fontSize: 13, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
            ],
          ),
        ),
      ),
    );
  }
}
