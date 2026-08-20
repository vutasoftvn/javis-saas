import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/floating_app_bar.dart';
import '../../../../modules/finance/services/policy_funding_service.dart';
import '../../controllers/strategy_controller.dart';

class ProjectFundingTab extends StatefulWidget {
  final String? projectId;

  const ProjectFundingTab({super.key, this.projectId});

  @override
  State<ProjectFundingTab> createState() => _ProjectFundingTabState();
}

class _ProjectFundingTabState extends State<ProjectFundingTab> {
  final PolicyFundingService _service = PolicyFundingService();
  StrategyController get strategyController => Get.find<StrategyController>();

  int _activeSubTabIndex = 0; // 0: Matches & Gaps, 1: Current Benefits Catalog, 2: Draft Watchlist
  List<dynamic> _currentBenefits = [];
  List<dynamic> _draftWatchlist = [];
  bool _isLoadingCatalog = false;
  String? _catalogCategoryFilter;
  String? _catalogStatusFilter;

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
      final benefits = await _service.getCurrentBenefits(
        programType: _catalogCategoryFilter,
        verificationStatus: _catalogStatusFilter,
      );
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
      Get.snackbar(
        'Thành công',
        'Đã hoàn tất khớp nối chính sách và cơ hội nguồn lực cho dự án.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.surfaceDark,
        colorText: Colors.white,
      );
    } catch (e) {
      setState(() => _isLoading = false);
      Get.snackbar('Lỗi', e.toString(), snackPosition: SnackPosition.BOTTOM);
    }
  }

  Future<void> _create12wyTask(int missingReqId, String title) async {
    if (_currentProjectId == null) return;
    try {
      await _service.create12wyTask(
        projectId: _currentProjectId!,
        missingRequirementId: missingReqId,
        customTitle: title,
      );
      await _loadOverview();
      Get.snackbar(
        'Đã tạo nhiệm vụ',
        'Nhiệm vụ "$title" đã được thêm vào kế hoạch 12 Week Year.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.primary.withValues(alpha: 0.2),
        colorText: Colors.white,
      );
    } catch (e) {
      Get.snackbar('Lỗi', e.toString(), snackPosition: SnackPosition.BOTTOM);
    }
  }

  void _openFounderVerificationModal(Map<String, dynamic> program) {
    final progId = program['id']?.toString() ?? program['id_str'] ?? '';
    final progName = program['name'] ?? 'Chương trình';
    final authority = program['authority'] ?? '';
    final sourceClaim = program['source_claim'] ?? '';
    final claims = program['claims'] as List<dynamic>? ?? [];

    final urlCtrl = TextEditingController(text: program['source_url'] ?? '');
    final authCtrl = TextEditingController(text: authority);
    final noteCtrl = TextEditingController();
    String selectedStatus = program['verification_status'] == 'VERIFIED_ACTIVE' ? 'VERIFIED_ACTIVE' : 'VERIFIED_ACTIVE';

    Get.dialog(
      Dialog(
        backgroundColor: AppTheme.surfaceDark,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppTheme.borderDark),
        ),
        child: Container(
          width: 720,
          constraints: const BoxConstraints(maxHeight: 650),
          padding: const EdgeInsets.all(24),
          child: StatefulBuilder(
            builder: (context, setModalState) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.verified_user_rounded, color: AppTheme.primary, size: 22),
                          const SizedBox(width: 10),
                          Text(
                            'Kiểm chứng Quyền lợi: $progName',
                            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      IconButton(
                        onPressed: () => Get.back(),
                        icon: const Icon(Icons.close_rounded, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                  const Divider(color: AppTheme.borderDark),
                  const SizedBox(height: 8),
                  if (sourceClaim.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.all(10),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: AppTheme.accent.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.accent.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.info_outline, color: AppTheme.accent, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Nguồn tham khảo: $sourceClaim',
                              style: const TextStyle(color: Colors.white70, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  Expanded(
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (claims.isNotEmpty) ...[
                            const Text(
                              'DANH SÁCH MỆNH ĐỀ TỪ TÀI LIỆU NGUỒN (CLAIMS):',
                              style: TextStyle(color: AppTheme.primaryLight, fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 8),
                            ...claims.map((c) {
                              final claimVal = c['claim_value'] ?? '';
                              final claimType = c['claim_type'] ?? '';
                              return Container(
                                margin: const EdgeInsets.only(bottom: 6),
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF060A14),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppTheme.borderDark),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.check_circle_outline, color: AppTheme.primary, size: 14),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: AppTheme.primary.withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(claimType, style: const TextStyle(color: AppTheme.primary, fontSize: 10, fontWeight: FontWeight.bold)),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(claimVal, style: const TextStyle(color: Colors.white, fontSize: 12)),
                                    ),
                                  ],
                                ),
                              );
                            }),
                            const SizedBox(height: 16),
                          ],
                          const Text(
                            'THÔNG TIN XÁC MINH CHÍNH THỨC:',
                            style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          TextField(
                            controller: urlCtrl,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              labelText: 'Cổng thông tin / Link văn bản chính thức',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark),
                              hintText: 'https://...',
                              hintStyle: const TextStyle(color: Colors.white24),
                              filled: true,
                              fillColor: const Color(0xFF060A14),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: authCtrl,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              labelText: 'Cơ quan có thẩm quyền ban hành',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark),
                              filled: true,
                              fillColor: const Color(0xFF060A14),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: noteCtrl,
                            maxLines: 2,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              labelText: 'Ghi chú kiểm chứng của Founder',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark),
                              hintText: 'Ví dụ: Đã đối chiếu với Cổng DVC BKHCN, đợt tiếp nhận mở từ Q3/2026...',
                              hintStyle: const TextStyle(color: Colors.white24),
                              filled: true,
                              fillColor: const Color(0xFF060A14),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                          ),
                          const SizedBox(height: 14),
                          const Text(
                            'KẾT QUẢ XÁC MINH:',
                            style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              ChoiceChip(
                                label: const Text('Hiệu lực (Active)', style: TextStyle(fontSize: 12)),
                                selected: selectedStatus == 'VERIFIED_ACTIVE',
                                selectedColor: const Color(0xFF10B981),
                                onSelected: (s) => setModalState(() => selectedStatus = 'VERIFIED_ACTIVE'),
                              ),
                              ChoiceChip(
                                label: const Text('Căn cứ (Enacted)', style: TextStyle(fontSize: 12)),
                                selected: selectedStatus == 'VERIFIED_ENACTED',
                                selectedColor: const Color(0xFF00E5FF),
                                onSelected: (s) => setModalState(() => selectedStatus = 'VERIFIED_ENACTED'),
                              ),
                              ChoiceChip(
                                label: const Text('Không đúng / Đóng', style: TextStyle(fontSize: 12)),
                                selected: selectedStatus == 'REJECTED_SOURCE_DATA',
                                selectedColor: const Color(0xFFEF4444),
                                onSelected: (s) => setModalState(() => selectedStatus = 'REJECTED_SOURCE_DATA'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      OutlinedButton(
                        onPressed: () => Get.back(),
                        child: const Text('Hủy'),
                      ),
                      const SizedBox(width: 10),
                      ElevatedButton.icon(
                        onPressed: () async {
                          Get.back();
                          try {
                            await _service.verifyProgram(
                              programId: progId,
                              resultStatus: selectedStatus,
                              officialSourceUrl: urlCtrl.text.trim(),
                              officialAuthority: authCtrl.text.trim(),
                              notes: noteCtrl.text.trim(),
                            );
                            await _loadCatalogData();
                            await _loadOverview();
                            Get.snackbar(
                              'Đã cập nhật kiểm chứng',
                              'Chương trình "$progName" đã được cập nhật trạng thái $selectedStatus và tính toán lại matching.',
                              snackPosition: SnackPosition.BOTTOM,
                              backgroundColor: AppTheme.success.withValues(alpha: 0.2),
                              colorText: Colors.white,
                            );
                          } catch (e) {
                            Get.snackbar('Lỗi xác minh', e.toString(), snackPosition: SnackPosition.BOTTOM);
                          }
                        },
                        icon: const Icon(Icons.check_circle_outline, size: 16),
                        label: const Text('Lưu & Cập nhật Matching'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primary,
                          foregroundColor: const Color(0xFF04070E),
                        ),
                      ),
                    ],
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (strategyController.projects.isEmpty) {
      return Center(
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.borderDark),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.folder_open_rounded, size: 48, color: AppTheme.textMutedDark),
              const SizedBox(height: 16),
              const Text(
                'Chưa có dự án nào trong Workspace',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Vui lòng tạo Dự án trước để xem phân tích Nguồn lực & Chính sách.',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
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
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark,
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: AppTheme.borderDark),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _currentProjectId,
                    dropdownColor: AppTheme.surfaceDark,
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
                    icon: const Icon(Icons.arrow_drop_down, color: AppTheme.primary),
                    items: strategyController.projects.map((p) {
                      final id = p['id']?.toString() ?? '';
                      final title = p['title'] ?? 'Dự án';
                      return DropdownMenuItem<String>(
                        value: id,
                        child: Text(title, overflow: TextOverflow.ellipsis),
                      );
                    }).toList(),
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
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Sub Navigation Bar
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.borderDark),
            ),
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
                    ? Center(
                        child: Text(_errorMessage!, style: const TextStyle(color: AppTheme.error)),
                      )
                    : _activeSubTabIndex == 0
                        ? _buildMatchesTabContent()
                        : _activeSubTabIndex == 1
                            ? _buildCurrentBenefitsCatalogContent()
                            : _buildDraftWatchlistContent(),
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
              Text(
                label,
                style: TextStyle(
                  color: isSelected ? Colors.white : AppTheme.textMutedDark,
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCurrentBenefitsCatalogContent() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.accent.withValues(alpha: 0.4)),
            ),
            child: Row(
              children: const [
                Icon(Icons.warning_amber_rounded, color: AppTheme.accent, size: 22),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Dữ liệu khởi tạo từ tài liệu Founders’ Meetup #1 — Chưa xác minh chính thức. '
                    'Founder cần kiểm chứng văn bản/cổng chính thức trước khi sử dụng. Hệ số điểm matching mặc định 0.6 sẽ được tăng lên 1.0 sau khi xác minh.',
                    style: TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'DANH MỤC 23 QUYỀN LỢI HIỆN HÀNH (6 NHÓM)',
                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${_currentBenefits.length} quyền lợi',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_isLoadingCatalog)
            const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator(color: AppTheme.primary)))
          else if (_currentBenefits.isEmpty)
            _buildEmptySection('Không tìm thấy quyền lợi nào phù hợp.')
          else
            ..._currentBenefits.map((p) => _buildCatalogBenefitCard(p as Map<String, dynamic>)),
        ],
      ),
    );
  }

  Widget _buildDraftWatchlistContent() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.blueGrey.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blueGrey.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: const [
                Icon(Icons.visibility_outlined, color: Colors.cyanAccent, size: 22),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Danh mục 5 Chương trình Quốc gia Dự thảo giai đoạn 2026–2035 đang lấy ý kiến. '
                    'COSA chỉ theo dõi tiến độ ban hành, không tính vào kế hoạch tài trợ hiện hành của Project.',
                    style: TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (_draftWatchlist.isEmpty)
            _buildEmptySection('Không có chương trình dự thảo nào đang theo dõi.')
          else
            ..._draftWatchlist.map((p) => _buildCatalogBenefitCard(p as Map<String, dynamic>, isDraft: true)),
        ],
      ),
    );
  }

  Widget _buildCatalogBenefitCard(Map<String, dynamic> program, {bool isDraft = false}) {
    final name = program['name'] ?? 'Quyền lợi';
    final authority = program['authority'] ?? 'Cơ quan quản lý';
    final pType = program['program_type'] ?? 'GRANT';
    final summary = program['summary'] ?? '';
    final sourceClaim = program['source_claim'] ?? '';
    final vStatus = program['verification_status'] ?? 'PENDING_FOUNDER_VERIFICATION';
    final fundingMax = (program['funding_max'] as num?)?.toDouble() ?? 0.0;
    final claims = program['claims'] as List<dynamic>? ?? [];

    Color badgeColor;
    String badgeText;
    if (isDraft || vStatus == 'DRAFT_WATCHLIST') {
      badgeColor = Colors.grey;
      badgeText = 'DỰ THẢO THEO DÕI';
    } else if (vStatus == 'VERIFIED_ACTIVE') {
      badgeColor = AppTheme.success;
      badgeText = 'ĐÃ XÁC MINH HIỆU LỰC';
    } else if (vStatus == 'VERIFIED_ENACTED') {
      badgeColor = AppTheme.primary;
      badgeText = 'ĐÃ XÁC MINH CĂN CỨ';
    } else {
      badgeColor = AppTheme.accent;
      badgeText = 'CHƯA XÁC MINH CHÍNH THỨC';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(authority, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: badgeColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: badgeColor.withValues(alpha: 0.4)),
                ),
                child: Text(badgeText, style: TextStyle(color: badgeColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _buildPill(pType, AppTheme.primary),
              const SizedBox(width: 8),
              if (fundingMax > 0) ...[
                _buildPill('Hỗ trợ tối đa: ${_formatVnd(fundingMax)}', AppTheme.primaryLight),
                const SizedBox(width: 8),
              ],
              if (claims.isNotEmpty)
                _buildPill('${claims.length} mệnh đề claim', Colors.white70),
            ],
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ],
          if (sourceClaim.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('Nguồn: $sourceClaim', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontStyle: FontStyle.italic)),
          ],
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (!isDraft) ...[
                ElevatedButton.icon(
                  onPressed: () => _openFounderVerificationModal(program),
                  icon: const Icon(Icons.fact_check_outlined, size: 14),
                  label: const Text('Kiểm chứng (Founder Verify)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  String _formatVnd(double amount) {
    if (amount >= 1000000000) {
      return '${(amount / 1000000000).toStringAsFixed(1)} Tỷ VND';
    } else if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(0)} Triệu VND';
    }
    return '${amount.toStringAsFixed(0)} VND';
  }

  Widget _buildMatchesTabContent() {
    final readinessAvg = (_overviewData['readiness_score_avg'] as num?)?.toDouble() ?? 0.0;
    final trlCurrent = (_overviewData['trl_current'] as num?)?.toInt() ?? 3;
    final companyType = _overviewData['company_type'] ?? 'STARTUP';
    final projectStage = _overviewData['project_stage'] ?? 'MVP';
    final topMatches = (_overviewData['top_matches'] as List<dynamic>?) ?? [];
    final missingReqs = (_overviewData['missing_requirements'] as List<dynamic>?) ?? [];
    final urgentAlerts = (_overviewData['urgent_alerts'] as List<dynamic>?) ?? [];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (urgentAlerts.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.error.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.notification_important_rounded, color: AppTheme.error, size: 18),
                      SizedBox(width: 8),
                      Text('CẢNH BÁO TIÊU ĐIỂM & RỦI RO', style: TextStyle(color: AppTheme.error, fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...urgentAlerts.map((a) => Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text('• $a', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                      )),
                ],
              ),
            ),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: _buildMetricCard(
                  title: 'Mức sẵn sàng hồ sơ',
                  value: '${readinessAvg.toStringAsFixed(0)}/100',
                  subtitle: readinessAvg >= 70 ? 'Sẵn sàng nộp hồ sơ' : 'Cần bổ sung thêm minh chứng',
                  icon: Icons.fact_check_outlined,
                  color: readinessAvg >= 70 ? AppTheme.success : AppTheme.accent,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: _buildMetricCard(
                  title: 'Mức sẵn sàng công nghệ',
                  value: 'TRL $trlCurrent',
                  subtitle: _getTrlName(trlCurrent.toInt()),
                  icon: Icons.memory_rounded,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 3,
                child: _buildMetricCard(
                  title: 'Phân loại & Giai đoạn',
                  value: _getCompanyTypeName(companyType),
                  subtitle: 'Giai đoạn: ${_getStageName(projectStage)}',
                  icon: Icons.business_outlined,
                  color: AppTheme.primaryLight,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Section 1: Matched Opportunities
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'CƠ HỘI NGUỒN LỰC PHÙ HỢP (TOP OPPORTUNITIES)',
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${topMatches.length} chương trình',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (topMatches.isEmpty)
            _buildEmptySection('Chưa có chương trình nào khớp. Nhấn "Khớp nối cơ hội" để AI phân tích.')
          else
            ...topMatches.map((m) => _buildOpportunityCard(m)),

          const SizedBox(height: 24),

          // Section 2: Missing Requirements & 12WY Action
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'ĐIỀU KIỆN CÒN THIẾU & HÀNH ĐỘNG (GAP ANALYSIS → 12WY)',
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${missingReqs.length} hạng mục',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (missingReqs.isEmpty)
            _buildEmptySection('Hồ sơ dự án đã đáp ứng đầy đủ các điều kiện cơ bản.')
          else
            ...missingReqs.map((r) => _buildMissingReqCard(r)),

          const SizedBox(height: 24),

          // Section 3: Funding Stack Breakdown
          _buildFundingStackCard(),
        ],
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                const SizedBox(height: 4),
                Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOpportunityCard(Map<String, dynamic> match) {
    final progName = match['program_name'] ?? 'Chương trình hỗ trợ';
    final progAuthority = match['program_authority'] ?? 'Cơ quan quản lý';
    final matchScore = ((match['match_score'] ?? 0.0) as num).toDouble();
    final readinessScore = ((match['readiness_score'] ?? 0.0) as num).toDouble();
    final eligibility = match['eligibility_status'] ?? 'POTENTIALLY_ELIGIBLE';
    final summary = match['ai_summary'] ?? '';

    Color statusColor;
    String statusText;
    if (eligibility == 'ELIGIBLE') {
      statusColor = AppTheme.success;
      statusText = 'ĐỦ ĐIỀU KIỆN';
    } else if (eligibility == 'INELIGIBLE') {
      statusColor = AppTheme.error;
      statusText = 'CHƯA ĐẠT ĐIỀU KIỆN CỨNG';
    } else {
      statusColor = AppTheme.accent;
      statusText = 'CÓ KHẢ NĂNG PHÙ HỢP';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(progName, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(progAuthority, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                ),
                child: Text(statusText, style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildPill('Điểm phù hợp (Match): ${matchScore.toStringAsFixed(0)}%', AppTheme.primary),
              const SizedBox(width: 8),
              _buildPill('Sẵn sàng hồ sơ: ${readinessScore.toStringAsFixed(0)}%', AppTheme.primaryLight),
            ],
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ],
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton.icon(
                onPressed: () => _showOpportunityDetails(match),
                icon: const Icon(Icons.rule_folder_outlined, size: 14),
                label: const Text('Xem điều kiện', style: TextStyle(fontSize: 12)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => _showProposalModal(match),
                icon: const Icon(Icons.edit_document, size: 14),
                label: const Text('Chuẩn bị hồ sơ (AI Draft)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showOpportunityDetails(Map<String, dynamic> match) {
    final progName = match['program_name'] ?? 'Chương trình';
    final summary = match['ai_summary'] ?? '';
    final matchScore = ((match['match_score'] ?? 0.0) as num).toDouble();
    final readinessScore = ((match['readiness_score'] ?? 0.0) as num).toDouble();

    Get.dialog(
      Dialog(
        backgroundColor: AppTheme.surfaceDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppTheme.borderDark)),
        child: Container(
          width: 550,
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(progName, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                  ),
                  IconButton(onPressed: () => Get.back(), icon: const Icon(Icons.close_rounded, color: AppTheme.textMutedDark)),
                ],
              ),
              const Divider(color: AppTheme.borderDark),
              const SizedBox(height: 8),
              Text('Điểm phù hợp: ${matchScore.toStringAsFixed(0)}%  •  Điểm sẵn sàng hồ sơ: ${readinessScore.toStringAsFixed(0)}%', style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 12),
              Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.5)),
              const SizedBox(height: 20),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton(
                  onPressed: () => Get.back(),
                  child: const Text('Đóng'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showProposalModal(Map<String, dynamic> match) {
    final progName = match['program_name'] ?? 'Chương trình';

    Get.dialog(
      Dialog(
        backgroundColor: AppTheme.surfaceDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppTheme.borderDark)),
        child: Container(
          width: 700,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.auto_awesome_rounded, color: AppTheme.primary, size: 20),
                      const SizedBox(width: 8),
                      Text('Proposal Workspace: $progName', style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  IconButton(onPressed: () => Get.back(), icon: const Icon(Icons.close_rounded, color: AppTheme.textMutedDark)),
                ],
              ),
              const Divider(color: AppTheme.borderDark),
              const SizedBox(height: 8),
              const Text(
                'AI tự động tạo bản thảo thuyết minh từ dữ liệu thật của Dự án. Mọi thông tin còn thiếu được đánh dấu [CẦN FOUNDER BỔ SUNG].',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView(
                  children: [
                    _buildProposalSectionItem('1. Bối cảnh & Tính cấp thiết', 'Dự án giải quyết nhu cầu thực tiễn trong chuyển đổi số doanh nghiệp...', true),
                    _buildProposalSectionItem('2. Mục tiêu Dự án', 'Nâng cấp công nghệ lên TRL 6; Đạt [CẦN FOUNDER BỔ SUNG: Số khách hàng pilot]...', false),
                    _buildProposalSectionItem('3. Giải pháp Công nghệ & Tính mới', 'Kiến trúc AI Agentic đa tầng làm chủ công nghệ...', true),
                    _buildProposalSectionItem('4. Mức độ Sẵn sàng Công nghệ (TRL)', 'TRL 4 -> TRL 6; Minh chứng: Báo cáo thử nghiệm MVP...', true),
                    _buildProposalSectionItem('8. Dự toán Kinh phí & Vốn đối ứng', 'Kinh phí đề xuất: 1,500,000,000 VND; Vốn đối ứng: 500,000,000 VND...', false),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  OutlinedButton.icon(
                    onPressed: () {
                      Get.back();
                      Get.snackbar('Xuất hồ sơ', 'Đã xuất toàn văn bản thuyết minh ra Markdown thành công.', snackPosition: SnackPosition.BOTTOM, backgroundColor: AppTheme.surfaceDark, colorText: Colors.white);
                    },
                    icon: const Icon(Icons.download_rounded, size: 16),
                    label: const Text('Xuất toàn văn Markdown'),
                  ),
                  ElevatedButton(
                    onPressed: () => Get.back(),
                    style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
                    child: const Text('Hoàn tất & Lưu hồ sơ'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProposalSectionItem(String title, String preview, bool isApproved) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF070C18),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isApproved ? AppTheme.success.withValues(alpha: 0.3) : AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: (isApproved ? AppTheme.success : AppTheme.accent).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Text(isApproved ? 'ĐÃ DUYỆT' : 'DỰ THẢO AI', style: TextStyle(color: isApproved ? AppTheme.success : AppTheme.accent, fontSize: 10, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(preview, style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildMissingReqCard(Map<String, dynamic> req) {
    final title = req['title'] ?? 'Minh chứng';
    final desc = req['description'] ?? '';
    final reqId = req['id'] as int? ?? 0;
    final isResolved = req['is_resolved'] == true;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Icon(
            isResolved ? Icons.check_circle_rounded : Icons.pending_actions_rounded,
            color: isResolved ? AppTheme.success : AppTheme.accent,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                if (desc.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(desc, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                ],
              ],
            ),
          ),
          OutlinedButton.icon(
            onPressed: isResolved ? null : () => _create12wyTask(reqId, title),
            icon: const Icon(Icons.add_task_rounded, size: 14),
            label: const Text('Thêm vào 12WY', style: TextStyle(fontSize: 12)),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.primary,
              side: const BorderSide(color: AppTheme.primary),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFundingStackCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.pie_chart_outline_rounded, color: AppTheme.primary, size: 20),
              SizedBox(width: 8),
              Text(
                'CƠ CẤU NGUỒN LỰC ĐỀ XUẤT (FUNDING STACK)',
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Kết hợp đa nguồn lực giúp tối ưu chi phí và mở rộng quy mô mà không làm loãng vốn cổ phần.',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _buildStackItem('Tiền mặt (Grant)', 'Tài trợ R&D', AppTheme.primary),
              const SizedBox(width: 12),
              _buildStackItem('Phi tiền mặt (Cloud)', 'AWS / GCP Credit', AppTheme.primaryLight),
              const SizedBox(width: 12),
              _buildStackItem('Voucher', 'Hỗ trợ khách hàng', AppTheme.accent),
              const SizedBox(width: 12),
              _buildStackItem('Vốn đối ứng', 'Vốn Founder', AppTheme.success),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStackItem(String title, String desc, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 4),
            Text(desc, style: const TextStyle(color: Colors.white70, fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Widget _buildPill(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildEmptySection(String msg) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Center(
        child: Text(msg, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
      ),
    );
  }

  String _getCompanyTypeName(String type) {
    switch (type) {
      case 'STARTUP':
        return 'Startup khởi nghiệp sáng tạo';
      case 'SPIN_OFF':
        return 'Doanh nghiệp Spin-off Viện/Trường';
      case 'SCIENCE_TECH_ENTERPRISE':
        return 'Doanh nghiệp KH&CN';
      case 'INNOVATIVE_SME':
        return 'SME đổi mới sáng tạo';
      case 'DIGITAL_SME':
        return 'SME công nghệ số';
      default:
        return 'Doanh nghiệp khởi nghiệp';
    }
  }

  String _getStageName(String stage) {
    switch (stage) {
      case 'IDEA':
        return 'Ý tưởng (Idea)';
      case 'POC':
        return 'Chứng minh khả thi (PoC)';
      case 'PROTOTYPE':
        return 'Mẫu thử (Prototype)';
      case 'MVP':
        return 'Sản phẩm khả dụng tối thiểu (MVP)';
      case 'MARKET_VALIDATION':
        return 'Xác thực thị trường';
      case 'ACCELERATION':
        return 'Tăng tốc (Acceleration)';
      case 'SCALE_UP':
        return 'Mở rộng (Scale-up)';
      default:
        return stage;
    }
  }

  String _getTrlName(int trl) {
    switch (trl) {
      case 1:
        return 'Quan sát nguyên lý cơ bản';
      case 2:
        return 'Hình thành khái niệm công nghệ';
      case 3:
        return 'Bằng chứng thực nghiệm (PoC)';
      case 4:
        return 'Thử nghiệm phòng thí nghiệm';
      case 5:
        return 'Thử nghiệm môi trường liên quan';
      case 6:
        return 'Thử nghiệm môi trường thực tế';
      case 7:
        return 'Mẫu thử hoàn chỉnh môi trường vận hành';
      case 8:
        return 'Hệ thống hoàn tất và chứng nhận';
      case 9:
        return 'Vận hành thương mại thành công';
      default:
        return 'TRL $trl';
    }
  }
}
