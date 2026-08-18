import 'package:flutter/material.dart';
import '../../../data/models/stage_model.dart';
import '../presentation/widgets/glass_card.dart';

class CompanyActivationCard extends StatefulWidget {
  final Function({
    required String companyName,
    required String industry,
    required String businessModel,
    required String vision,
    required String mission,
    required String projectTitle,
    required ProjectStage stage,
    required String jobToBeDone,
    required String problemStatement,
    required String currentAlternative,
  }) onCompleteActivation;
  final bool isLoading;

  const CompanyActivationCard({
    super.key,
    required this.onCompleteActivation,
    this.isLoading = false,
  });

  @override
  State<CompanyActivationCard> createState() => _CompanyActivationCardState();
}

class _CompanyActivationCardState extends State<CompanyActivationCard> {
  int _currentStep = 0;
  String? _errorMessage;

  // Step 1: Company Profile
  final _companyNameController = TextEditingController();
  String _selectedIndustry = 'Công nghệ / Phần mềm (SaaS)';
  String _selectedBusinessModel = 'B2B (Bán cho doanh nghiệp)';
  final _visionController = TextEditingController();
  final _missionController = TextEditingController();

  // Step 2: Project & Stage
  final _projectTitleController = TextEditingController();
  ProjectStage _selectedStage = ProjectStage.s1ProblemValidation;

  // Step 3: Knowledge & Problem Context
  final _jtbdController = TextEditingController();
  final _problemController = TextEditingController();
  final _currentAlternativeController = TextEditingController();

  final List<String> _industries = [
    'Công nghệ / Phần mềm (SaaS)',
    'Thương mại điện tử & D2C',
    'F&B & Bán lẻ',
    'Dịch vụ Chuyên nghiệp / Agency',
    'Sản xuất & Vận hành chuỗi',
    'Tài chính / Fintech / Edtech',
    'Khác',
  ];

  final List<String> _businessModels = [
    'B2B (Bán cho doanh nghiệp)',
    'B2C (Bán cho người tiêu dùng cá nhân)',
    'B2B2C / Marketplace nền tảng',
    'Dịch vụ / Tư vấn chuyên sâu',
  ];

  @override
  void initState() {
    super.initState();
    _companyNameController.addListener(_onFieldChanged);
    _visionController.addListener(_onFieldChanged);
    _missionController.addListener(_onFieldChanged);
    _projectTitleController.addListener(_onFieldChanged);
    _jtbdController.addListener(_onFieldChanged);
    _problemController.addListener(_onFieldChanged);
    _currentAlternativeController.addListener(_onFieldChanged);
  }

  void _onFieldChanged() {
    if (mounted) {
      if (_errorMessage != null && _isCurrentStepValid) {
        setState(() {
          _errorMessage = null;
        });
      } else {
        setState(() {});
      }
    }
  }

  @override
  void dispose() {
    _companyNameController.removeListener(_onFieldChanged);
    _visionController.removeListener(_onFieldChanged);
    _missionController.removeListener(_onFieldChanged);
    _projectTitleController.removeListener(_onFieldChanged);
    _jtbdController.removeListener(_onFieldChanged);
    _problemController.removeListener(_onFieldChanged);
    _currentAlternativeController.removeListener(_onFieldChanged);

    _companyNameController.dispose();
    _visionController.dispose();
    _missionController.dispose();
    _projectTitleController.dispose();
    _jtbdController.dispose();
    _problemController.dispose();
    _currentAlternativeController.dispose();
    super.dispose();
  }

  bool get _isCurrentStepValid {
    if (_currentStep == 0) {
      return _companyNameController.text.trim().isNotEmpty &&
          _visionController.text.trim().isNotEmpty &&
          _missionController.text.trim().isNotEmpty;
    } else if (_currentStep == 1) {
      return _projectTitleController.text.trim().isNotEmpty;
    } else if (_currentStep == 2) {
      return _problemController.text.trim().isNotEmpty &&
          _jtbdController.text.trim().isNotEmpty &&
          _currentAlternativeController.text.trim().isNotEmpty;
    } else if (_currentStep == 3) {
      return _companyNameController.text.trim().isNotEmpty &&
          _visionController.text.trim().isNotEmpty &&
          _missionController.text.trim().isNotEmpty &&
          _projectTitleController.text.trim().isNotEmpty &&
          _problemController.text.trim().isNotEmpty &&
          _jtbdController.text.trim().isNotEmpty &&
          _currentAlternativeController.text.trim().isNotEmpty;
    }
    return true;
  }

  void _suggestAiFoundation() {
    final compName = _companyNameController.text.trim().isNotEmpty
        ? _companyNameController.text.trim()
        : 'Doanh nghiệp';
    setState(() {
      _errorMessage = null;
      _visionController.text =
          'Đưa $compName trở thành thương hiệu dẫn đầu trong ngành $_selectedIndustry, tiên phong ứng dụng AI để tối ưu hiệu suất.';
      _missionController.text =
          'Cung cấp giải pháp vượt trội giúp khách hàng giải quyết triệt để bài toán vận hành và tăng trưởng bền vững.';
    });
  }

  void _suggestAiProblemContext() {
    final proj = _projectTitleController.text.trim().isNotEmpty
        ? _projectTitleController.text.trim()
        : 'Dự án cốt lõi';
    setState(() {
      _errorMessage = null;
      _jtbdController.text = 'Giúp khách hàng đạt được kết quả vượt trội với $proj, tự động hoá quy trình và tiết kiệm 70% thời gian.';
      _problemController.text = 'Khách hàng đang mất nhiều thời gian, nhân lực và dễ sai sót khi vận hành thủ công.';
      _currentAlternativeController.text = 'File Excel rời rạc + Trao đổi qua chat thông thường + Nhắc việc thủ công.';
    });
  }

  bool _validateStep(int step) {
    if (step == 0) {
      if (_companyNameController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Tên Doanh Nghiệp / Công ty để tiếp tục.';
        return false;
      }
      if (_visionController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Tầm nhìn (hoặc bấm "AI Tự Động Gợi Ý").';
        return false;
      }
      if (_missionController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Sứ mệnh (hoặc bấm "AI Tự Động Gợi Ý").';
        return false;
      }
    } else if (step == 1) {
      if (_projectTitleController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Tên Dự Án Cốt Lõi đầu tiên để tiếp tục.';
        return false;
      }
    } else if (step == 2) {
      if (_problemController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Nỗi đau / Bài toán cốt lõi (Problem Statement).';
        return false;
      }
      if (_jtbdController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Việc cần làm của khách hàng (Job-to-be-Done).';
        return false;
      }
      if (_currentAlternativeController.text.trim().isEmpty) {
        _errorMessage = 'Vui lòng nhập Giải pháp thay thế hiện tại (hoặc bấm "AI Tự Động Gợi Ý").';
        return false;
      }
    }
    _errorMessage = null;
    return true;
  }

  void _goToNextStep() {
    if (_validateStep(_currentStep)) {
      setState(() {
        _errorMessage = null;
        _currentStep++;
      });
    } else {
      setState(() {});
    }
  }

  void _onSelectStep(int index) {
    if (index < _currentStep) {
      setState(() {
        _errorMessage = null;
        _currentStep = index;
      });
    } else if (index > _currentStep) {
      for (int i = 0; i < index; i++) {
        if (!_validateStep(i)) {
          setState(() {
            _currentStep = i;
          });
          return;
        }
      }
      setState(() {
        _errorMessage = null;
        _currentStep = index;
      });
    }
  }

  void _submitActivation() {
    for (int i = 0; i < 3; i++) {
      if (!_validateStep(i)) {
        setState(() {
          _currentStep = i;
        });
        return;
      }
    }

    final companyName = _companyNameController.text.trim();
    final projectTitle = _projectTitleController.text.trim();

    widget.onCompleteActivation(
      companyName: companyName,
      industry: _selectedIndustry,
      businessModel: _selectedBusinessModel,
      vision: _visionController.text.trim(),
      mission: _missionController.text.trim(),
      projectTitle: projectTitle,
      stage: _selectedStage,
      jobToBeDone: _jtbdController.text.trim(),
      problemStatement: _problemController.text.trim(),
      currentAlternative: _currentAlternativeController.text.trim(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      borderRadius: 20,
      padding: const EdgeInsets.all(24),
      borderColor: const Color(0xFF0EA5E9).withValues(alpha: 0.35),
      borderWidth: 1.2,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // ── Header Banner ────────────────────────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF0EA5E9), Color(0xFF6366F1)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF0EA5E9).withValues(alpha: 0.4),
                      blurRadius: 10,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.rocket_launch_rounded,
                  color: Colors.white,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0EA5E9).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(100),
                            border: Border.all(
                              color: const Color(0xFF0EA5E9).withValues(alpha: 0.4),
                            ),
                          ),
                          child: const Text(
                            'CHẾ ĐỘ KHỞI NGUYÊN • GENESIS SETUP',
                            style: TextStyle(
                              color: Color(0xFF38BDF8),
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.8,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Thiết Lập Doanh Nghiệp & Kích Hoạt AI',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.3,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Hoàn tất 4 bước định vị bắt buộc để AI phân tích ngữ cảnh, kích hoạt Sprint xác thực nhanh hoặc Chu kỳ tăng trưởng.',
                      style: TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 12.5,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // ── 4-Step Progress Bar ──────────────────────────────────────────
          _buildStepIndicators(),

          const SizedBox(height: 18),

          // ── Error Banner (Validation Message) ───────────────────────────
          if (_errorMessage != null) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: const Color(0xFFEF4444).withValues(alpha: 0.4),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded, color: Color(0xFFEF4444), size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(
                        color: Color(0xFFFCA5A5),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],

          const Divider(color: Colors.white10, height: 1),
          const SizedBox(height: 18),

          // ── Step Content ─────────────────────────────────────────────────
          if (_currentStep == 0) _buildStep1CompanyProfile(),
          if (_currentStep == 1) _buildStep2ProjectAndStage(),
          if (_currentStep == 2) _buildStep3KnowledgeContext(),
          if (_currentStep == 3) _buildStep4DiagnosticsAndLaunch(),

          const SizedBox(height: 24),

          // ── Bottom Action Controls ───────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (_currentStep > 0)
                OutlinedButton.icon(
                  onPressed: widget.isLoading ? null : () => setState(() {
                    _errorMessage = null;
                    _currentStep--;
                  }),
                  icon: const Icon(Icons.arrow_back_rounded, size: 16),
                  label: const Text('Quay lại'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF94A3B8),
                    side: const BorderSide(color: Colors.white24),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                )
              else
                const SizedBox.shrink(),
              Row(
                children: [
                  if (_currentStep < 3)
                    ElevatedButton.icon(
                      onPressed: _isCurrentStepValid ? _goToNextStep : null,
                      icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                      label: Text('Bước tiếp theo (${_currentStep + 2}/4)'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0EA5E9),
                        foregroundColor: Colors.white,
                        disabledBackgroundColor: const Color(0xFF1E293B).withValues(alpha: 0.7),
                        disabledForegroundColor: const Color(0xFF64748B),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                          side: BorderSide(
                            color: _isCurrentStepValid
                                ? const Color(0xFF0EA5E9)
                                : Colors.white10,
                          ),
                        ),
                        elevation: _isCurrentStepValid ? 4 : 0,
                      ),
                    )
                  else
                    ElevatedButton.icon(
                      onPressed: (widget.isLoading || !_isCurrentStepValid) ? null : _submitActivation,
                      icon: widget.isLoading
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.auto_awesome, size: 18),
                      label: Text(
                        widget.isLoading
                            ? 'Đang kích hoạt hệ thống...'
                            : 'Kích Hoạt Hệ Điều Hành AI',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10B981),
                        foregroundColor: Colors.white,
                        disabledBackgroundColor: const Color(0xFF1E293B).withValues(alpha: 0.7),
                        disabledForegroundColor: const Color(0xFF64748B),
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                          side: BorderSide(
                            color: _isCurrentStepValid
                                ? const Color(0xFF10B981)
                                : Colors.white10,
                          ),
                        ),
                        elevation: _isCurrentStepValid ? 6 : 0,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStepIndicators() {
    final stepTitles = [
      '1. Hồ sơ Doanh nghiệp',
      '2. Định vị Dự án',
      '3. Nạp Tri thức & JTBD',
      '4. AI Chẩn đoán',
    ];

    return Row(
      children: List.generate(4, (index) {
        final isCompleted = index < _currentStep;
        final isActive = index == _currentStep;
        final color = isCompleted
            ? const Color(0xFF10B981)
            : (isActive ? const Color(0xFF0EA5E9) : const Color(0xFF475569));

        return Expanded(
          child: InkWell(
            onTap: () => _onSelectStep(index),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
              margin: const EdgeInsets.symmetric(horizontal: 3),
              decoration: BoxDecoration(
                color: isActive ? color.withValues(alpha: 0.15) : Colors.transparent,
                borderRadius: BorderRadius.circular(8),
                border: Border(
                  bottom: BorderSide(
                    color: color,
                    width: isActive ? 2.5 : 1.5,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                      border: Border.all(color: color),
                    ),
                    child: Center(
                      child: isCompleted
                          ? const Icon(Icons.check, size: 12, color: Color(0xFF10B981))
                          : Text(
                              '${index + 1}',
                              style: TextStyle(
                                color: color,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      stepTitles[index],
                      style: TextStyle(
                        color: isActive ? Colors.white : const Color(0xFF94A3B8),
                        fontSize: 11,
                        fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }

  // ── Step 1: Company Profile ──────────────────────────────────────────────
  Widget _buildStep1CompanyProfile() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'BƯỚC 1: HỒ SƠ & BẢN SẮC DOANH NGHIỆP',
          style: TextStyle(
            color: Color(0xFF38BDF8),
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 14),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: _buildTextField(
                label: 'Tên Doanh Nghiệp / Công ty *',
                hint: 'Ví dụ: Miva Corp, TechFlow SaaS...',
                controller: _companyNameController,
                icon: Icons.business_rounded,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              flex: 3,
              child: _buildDropdown(
                label: 'Lĩnh vực / Ngành nghề',
                value: _selectedIndustry,
                items: _industries,
                onChanged: (v) => setState(() => _selectedIndustry = v!),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              flex: 3,
              child: _buildDropdown(
                label: 'Mô hình kinh doanh',
                value: _selectedBusinessModel,
                items: _businessModels,
                onChanged: (v) => setState(() => _selectedBusinessModel = v!),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Tầm nhìn & Sứ mệnh cốt lõi',
              style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600),
            ),
            TextButton.icon(
              onPressed: _suggestAiFoundation,
              icon: const Icon(Icons.auto_awesome, size: 14, color: Color(0xFF38BDF8)),
              label: const Text(
                'AI Tự Động Gợi Ý',
                style: TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              child: _buildTextField(
                label: 'Tầm nhìn (Vision)',
                hint: 'Đích đến trong 3-5 năm tới...',
                controller: _visionController,
                maxLines: 2,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _buildTextField(
                label: 'Sứ mệnh (Mission)',
                hint: 'Giá trị đem lại cho khách hàng hàng ngày...',
                controller: _missionController,
                maxLines: 2,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ── Step 2: Project & Stage Positioning ───────────────────────────────────
  Widget _buildStep2ProjectAndStage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'BƯỚC 2: ĐỊNH VỊ DỰ ÁN & GIAI ĐOẠN (STAGE POSITIONING)',
          style: TextStyle(
            color: Color(0xFF38BDF8),
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 14),
        _buildTextField(
          label: 'Tên Dự Án / Dòng Sản Phẩm Cốt Lõi Đầu Tiên *',
          hint: 'Ví dụ: Nền tảng Voice Agent AI, Phần mềm Quản lý F&B...',
          controller: _projectTitleController,
          icon: Icons.lightbulb_outline,
        ),
        const SizedBox(height: 16),
        const Text(
          'Chọn Giai đoạn thực tế của Dự án:',
          style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _buildStageChoiceCard(
              stage: ProjectStage.s0Explore,
              title: 'S0. Khám Phá Giả Định',
              subtitle: 'Chưa có ý tưởng rõ ràng, cần quét cơ hội thị trường.',
              track: '⚡ Validation Sprint (1-2 tuần)',
              trackColor: const Color(0xFF38BDF8),
            ),
            const SizedBox(width: 12),
            _buildStageChoiceCard(
              stage: ProjectStage.s1ProblemValidation,
              title: 'S1. Xác Thực Bài Toán',
              subtitle: 'Đang khảo sát nỗi đau khách hàng & JTBD thực tế.',
              track: '⚡ Validation Sprint (1-2 tuần)',
              trackColor: const Color(0xFF38BDF8),
            ),
            const SizedBox(width: 12),
            _buildStageChoiceCard(
              stage: ProjectStage.s2SolutionValidation,
              title: 'S2. Xác Thực Giải Pháp',
              subtitle: 'Đã có MVP/Nguyên mẫu, đang đo lường trả phí (WTP).',
              track: '⚡ Validation Sprint (1-2 tuần)',
              trackColor: const Color(0xFF38BDF8),
            ),
            const SizedBox(width: 12),
            _buildStageChoiceCard(
              stage: ProjectStage.s4GoToMarket,
              title: 'S3-S5. Tăng Trưởng & Vận Hành',
              subtitle: 'Đã có khách hàng trả tiền, cần mở rộng doanh thu.',
              track: '🎯 12-Week Growth Cycle',
              trackColor: const Color(0xFF10B981),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStageChoiceCard({
    required ProjectStage stage,
    required String title,
    required String subtitle,
    required String track,
    required Color trackColor,
  }) {
    final isSelected = _selectedStage == stage;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _selectedStage = stage),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: isSelected
                ? stage.primaryColor.withValues(alpha: 0.15)
                : const Color(0xFF0F172A).withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? stage.primaryColor : Colors.white12,
              width: isSelected ? 1.5 : 1.0,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        color: isSelected ? Colors.white : const Color(0xFFCBD5E1),
                        fontSize: 12.0,
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (isSelected) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.check_circle_rounded, color: stage.primaryColor, size: 16),
                  ],
                ],
              ),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11, height: 1.3),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: trackColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  track,
                  style: TextStyle(color: trackColor, fontSize: 9.5, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Step 3: Knowledge Context & Problem-First ──────────────────────────────
  Widget _buildStep3KnowledgeContext() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'BƯỚC 3: NẠP TRI THỨC & BÀI TOÁN KHÁCH HÀNG (PROBLEM-FIRST CONTEXT)',
              style: TextStyle(
                color: Color(0xFF38BDF8),
                fontSize: 13,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
            TextButton.icon(
              onPressed: _suggestAiProblemContext,
              icon: const Icon(Icons.auto_awesome, size: 14, color: Color(0xFF38BDF8)),
              label: const Text(
                'AI Tự Động Gợi Ý',
                style: TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _buildTextField(
                label: 'Nỗi đau / Bài toán cốt lõi (Problem Statement) *',
                hint: 'Mô tả vấn đề nghiêm trọng mà khách hàng đang chịu đựng...',
                controller: _problemController,
                maxLines: 3,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _buildTextField(
                label: 'Việc cần làm của khách hàng (Job-to-be-Done)',
                hint: 'Khách hàng muốn đạt được kết quả gì khi dùng sản phẩm...',
                controller: _jtbdController,
                maxLines: 3,
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        _buildTextField(
          label: 'Giải pháp thay thế hiện tại (Current Alternative)',
          hint: 'Khách hàng đang giải quyết vấn đề bằng cách nào (Excel, làm thủ công, đối thủ...)?',
          controller: _currentAlternativeController,
          maxLines: 2,
        ),
      ],
    );
  }

  // ── Step 4: AI Diagnostics & Launch ──────────────────────────────────────
  Widget _buildStep4DiagnosticsAndLaunch() {
    final isFastSprint = _selectedStage.index <= ProjectStage.s2SolutionValidation.index;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: (isFastSprint ? const Color(0xFF38BDF8) : const Color(0xFF10B981)).withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_awesome,
                color: isFastSprint ? const Color(0xFF38BDF8) : const Color(0xFF10B981),
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'BƯỚC 4: AI CHẨN ĐOÁN & ĐỊNH HÌNH LỘ TRÌNH TỐC ĐỘ CAO',
                style: TextStyle(
                  color: isFastSprint ? const Color(0xFF38BDF8) : const Color(0xFF10B981),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            isFastSprint
                ? '⚡ LỘ TRÌNH ĐƯỢC CHỌN: AI FAST VALIDATION SPRINT (1-2 TUẦN)\n'
                  'Dự án đang ở giai đoạn xác thực (${_selectedStage.displayNameVi}). Hệ thống sẽ KHÔNG ép chu kỳ 12 tuần cồng kềnh, '
                  'mà kích hoạt Sprint siêu tốc: AI tự tạo kịch bản phỏng vấn ICP, phân tích rủi ro Solution Bias và chuẩn bị bài đo Willingness-to-pay.'
                : '🎯 LỘ TRÌNH ĐƯỢC CHỌN: 12-WEEK GROWTH CYCLE (12 TUẦN QUẢN TRỊ)\n'
                  'Dự án đã có sản phẩm/khách hàng (${_selectedStage.displayNameVi}). Hệ thống sẽ kích hoạt Chu kỳ 12 tuần với bảng OKRs, '
                  'theo dõi chỉ số tài chính, phễu bán hàng và vận hành tự động hoá.',
            style: const TextStyle(color: Colors.white, fontSize: 12.5, height: 1.5),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black26,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                const Icon(Icons.check_circle_outline, color: Color(0xFF10B981), size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Doanh nghiệp: ${_companyNameController.text.isEmpty ? "Doanh nghiệp mới" : _companyNameController.text} • '
                    'Dự án: ${_projectTitleController.text.isEmpty ? "Dự án #1" : _projectTitleController.text} • '
                    'Ngành: $_selectedIndustry',
                    style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField({
    required String label,
    required String hint,
    required TextEditingController controller,
    IconData? icon,
    int maxLines = 1,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF94A3B8),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          maxLines: maxLines,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(color: Colors.white24, fontSize: 12.5),
            prefixIcon: icon != null ? Icon(icon, color: const Color(0xFF38BDF8), size: 18) : null,
            filled: true,
            fillColor: const Color(0xFF0F172A).withValues(alpha: 0.6),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Colors.white12),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Colors.white12),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xFF0EA5E9), width: 1.2),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDropdown({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    final effectiveValue = items.contains(value) ? value : (items.isNotEmpty ? items.first : null);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF94A3B8),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A).withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.white12),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: effectiveValue,
              isExpanded: true,
              dropdownColor: const Color(0xFF1E293B),
              style: const TextStyle(color: Colors.white, fontSize: 13),
              icon: const Icon(Icons.keyboard_arrow_down, color: Color(0xFF94A3B8), size: 18),
              items: items.map((item) {
                return DropdownMenuItem<String>(
                  value: item,
                  child: Text(item, overflow: TextOverflow.ellipsis),
                );
              }).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }
}
