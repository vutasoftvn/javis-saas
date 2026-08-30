import 'package:flutter/material.dart';
import '../../../data/models/stage_model.dart';
import '../presentation/widgets/glass_card.dart';
import 'activation/activation_step_indicators.dart';
import 'activation/activation_step1_profile.dart';
import 'activation/activation_step2_stage.dart';
import 'activation/activation_step3_context.dart';
import 'activation/activation_step4_diagnostics.dart';

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
  ProjectStage _selectedStage = ProjectStage.p1ProblemValidation;

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
      return _problemController.text.trim().isNotEmpty;
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
          // Header Banner
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
                child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0EA5E9).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(100),
                        border: Border.all(color: const Color(0xFF0EA5E9).withValues(alpha: 0.4)),
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
                    const SizedBox(height: 6),
                    const Text(
                      'Thiết Lập Doanh Nghiệp & Kích Hoạt AI',
                      style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 0.3),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Hoàn tất 4 bước định vị bắt buộc để AI phân tích ngữ cảnh, kích hoạt Sprint xác thực nhanh hoặc Chu kỳ tăng trưởng.',
                      style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // 4-Step Progress Bar
          ActivationStepIndicators(
            currentStep: _currentStep,
            onSelectStep: _onSelectStep,
          ),

          const SizedBox(height: 18),

          // Error Banner
          if (_errorMessage != null) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4), width: 1),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded, color: Color(0xFFEF4444), size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 12.5, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
          ],

          const Divider(color: Colors.white10, height: 1),
          const SizedBox(height: 18),

          // Step Contents
          if (_currentStep == 0)
            ActivationStep1Profile(
              companyNameController: _companyNameController,
              selectedIndustry: _selectedIndustry,
              industries: _industries,
              onIndustryChanged: (v) => setState(() => _selectedIndustry = v),
              selectedBusinessModel: _selectedBusinessModel,
              businessModels: _businessModels,
              onBusinessModelChanged: (v) => setState(() => _selectedBusinessModel = v),
              visionController: _visionController,
              missionController: _missionController,
              onSuggestAiFoundation: _suggestAiFoundation,
            ),
          if (_currentStep == 1)
            ActivationStep2Stage(
              projectTitleController: _projectTitleController,
              selectedStage: _selectedStage,
              onStageChanged: (stage) => setState(() => _selectedStage = stage),
            ),
          if (_currentStep == 2)
            ActivationStep3Context(
              problemController: _problemController,
              jtbdController: _jtbdController,
              currentAlternativeController: _currentAlternativeController,
              onSuggestAiProblemContext: _suggestAiProblemContext,
            ),
          if (_currentStep == 3)
            ActivationStep4Diagnostics(
              selectedStage: _selectedStage,
              companyName: _companyNameController.text,
              projectTitle: _projectTitleController.text,
              selectedIndustry: _selectedIndustry,
            ),

          const SizedBox(height: 24),

          // Bottom Action Controls
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
                            color: _isCurrentStepValid ? const Color(0xFF0EA5E9) : Colors.white10,
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
                        widget.isLoading ? 'Đang kích hoạt hệ thống...' : 'Kích Hoạt Hệ Điều Hành AI',
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
                            color: _isCurrentStepValid ? const Color(0xFF10B981) : Colors.white10,
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
}
