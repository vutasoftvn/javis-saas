// ignore_for_file: constant_identifier_names, deprecated_member_use
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../../../core/network/api_client.dart';
import '../../../core/theme/app_theme.dart';

enum FounderGoal {
  EXPERIMENT,
  SIDE_INCOME,
  SERVICE,
  PRODUCT,
  LEARN,
}

class VentureOnboardingScreen extends StatefulWidget {
  final Future<bool> Function({
    required String workspaceName,
    required String clientCreationId,
    required String problemStatement,
    required String targetCustomer,
    required FounderGoal goal,
  })? onComplete;

  const VentureOnboardingScreen({super.key, this.onComplete});

  @override
  State<VentureOnboardingScreen> createState() => _VentureOnboardingScreenState();
}

class _VentureOnboardingScreenState extends State<VentureOnboardingScreen> {
  int _currentStep = 0;
  final TextEditingController _problemController = TextEditingController();
  final TextEditingController _customerController = TextEditingController();
  final TextEditingController _workspaceNameController = TextEditingController();
  FounderGoal _selectedGoal = FounderGoal.EXPERIMENT;
  String? _clientCreationId;
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _clientCreationId = const Uuid().v4();
  }

  @override
  void dispose() {
    _problemController.dispose();
    _customerController.dispose();
    _workspaceNameController.dispose();
    super.dispose();
  }

  String get clientCreationId => _clientCreationId ??= const Uuid().v4();

  void _nextStep() {
    if (_currentStep == 0 && _problemController.text.trim().isEmpty) {
      setState(() => _errorMessage = 'Vui lòng nhập vấn đề bạn muốn giải quyết');
      return;
    }
    if (_currentStep == 1 && _customerController.text.trim().isEmpty) {
      setState(() => _errorMessage = 'Vui lòng nhập đối tượng gặp vấn đề');
      return;
    }
    if (_currentStep == 4 && _workspaceNameController.text.trim().isEmpty) {
      setState(() => _errorMessage = 'Vui lòng đặt tên cho Venture Workspace');
      return;
    }
    setState(() {
      _errorMessage = null;
      if (_currentStep < 4) {
        _currentStep++;
      }
    });
  }

  void _prevStep() {
    if (_currentStep > 0) {
      setState(() {
        _errorMessage = null;
        _currentStep--;
      });
    }
  }

  Future<void> _submit() async {
    if (_workspaceNameController.text.trim().isEmpty) {
      setState(() => _errorMessage = 'Vui lòng đặt tên cho Venture Workspace');
      return;
    }

    if (_isSubmitting) return; // Ngăn bấm 2 lần

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      if (widget.onComplete != null) {
        final ok = await widget.onComplete!(
          workspaceName: _workspaceNameController.text.trim(),
          clientCreationId: clientCreationId,
          problemStatement: _problemController.text.trim(),
          targetCustomer: _customerController.text.trim(),
          goal: _selectedGoal,
        );
        if (!ok) {
          setState(() => _errorMessage = 'Tạo workspace không thành công');
        }
      } else {
        // Mặc định gọi API đăng ký / tạo workspace
        final res = await ApiClient.post(
          '/platform/auth/register',
          body: {
            'workspace_name': _workspaceNameController.text.trim(),
            'client_workspace_creation_id': clientCreationId,
          },
        );
        if (res.statusCode != 200 && res.statusCode != 201) {
          setState(() => _errorMessage = 'Lỗi tạo workspace (${res.statusCode})');
        }
      }
    } catch (e) {
      setState(() => _errorMessage = 'Lỗi kết nối: $e');
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text('Khởi tạo Venture (Bước ${_currentStep + 1}/5)'),
        leading: _currentStep > 0
            ? IconButton(icon: const Icon(Icons.arrow_back), onPressed: _prevStep)
            : null,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              LinearProgressIndicator(
                value: (_currentStep + 1) / 5,
                backgroundColor: Colors.white10,
                valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.primary),
              ),
              const SizedBox(height: 24),
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.withValues(alpha: 0.5)),
                  ),
                  child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent)),
                ),
                const SizedBox(height: 16),
              ],
              _buildStepContent(),
              const SizedBox(height: 32),
              if (_currentStep < 4)
                ElevatedButton(
                  key: const Key('next_step_button'),
                  onPressed: _nextStep,
                  child: const Text('Tiếp tục'),
                )
              else
                ElevatedButton(
                  key: const Key('create_venture_button'),
                  onPressed: _isSubmitting ? null : _submit,
                  child: _isSubmitting
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('Tạo Venture Workspace Free'),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStepContent() {
    switch (_currentStep) {
      case 0:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Bạn đang muốn giải quyết điều gì?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            const Text(
              'Mô tả ngắn gọn vấn đề thực tế hoặc cơ hội bạn nhìn thấy.',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('problem_input'),
              controller: _problemController,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText: 'Ví dụ: Các chủ tiệm bánh mất 3 tiếng mỗi ngày để chốt sổ...',
              ),
            ),
          ],
        );
      case 1:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Ai đang gặp vấn đề đó?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            const Text(
              'Đối tượng khách hàng mục tiêu chịu nỗi đau nhiều nhất.',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('customer_input'),
              controller: _customerController,
              maxLines: 3,
              decoration: const InputDecoration(
                hintText: 'Ví dụ: Chủ tiệm bánh mì truyền thống tại Hà Nội...',
              ),
            ),
          ],
        );
      case 2:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Bạn muốn đạt điều gì trong 12 tuần tới?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 16),
            ...FounderGoal.values.map((g) {
              final title = _goalTitle(g);
              final subtitle = _goalSubtitle(g);
              return RadioListTile<FounderGoal>(
                key: Key('goal_${g.name}'),
                title: Text(title, style: const TextStyle(color: Colors.white)),
                subtitle: Text(subtitle, style: const TextStyle(color: AppTheme.textMutedDark)),
                value: g,
                groupValue: _selectedGoal,
                onChanged: (v) => setState(() => _selectedGoal = v!),
              );
            }),
          ],
        );
      case 3:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Bản đồ khởi đầu đề xuất',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white12),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Stage 0: Genesis -> Stage 1: Problem Validation',
                      style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary)),
                  SizedBox(height: 8),
                  Text('1. Phỏng vấn tối thiểu 5 khách hàng tiềm năng để xác minh vấn đề.',
                      style: TextStyle(color: Colors.white70)),
                  SizedBox(height: 4),
                  Text('2. Thu thập bằng chứng thực tế trước khi xây dựng sản phẩm.',
                      style: TextStyle(color: Colors.white70)),
                  SizedBox(height: 4),
                  Text('3. Đánh giá Gate S1 với số điểm bằng chứng >= 0.6.',
                      style: TextStyle(color: Colors.white70)),
                ],
              ),
            ),
          ],
        );
      case 4:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Đặt tên cho Venture Workspace Free',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            const Text(
              'Mỗi founder bắt đầu với gói Free, đầy đủ tính năng xác thực và lộ trình.',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('workspace_name_input'),
              controller: _workspaceNameController,
              decoration: const InputDecoration(
                hintText: 'Tên dự án / doanh nghiệp (ví dụ: Bánh Mì AI)',
              ),
            ),
          ],
        );
      default:
        return const SizedBox.shrink();
    }
  }

  String _goalTitle(FounderGoal g) {
    switch (g) {
      case FounderGoal.EXPERIMENT:
        return 'Thử nghiệm (Experiment)';
      case FounderGoal.SIDE_INCOME:
        return 'Thu nhập thêm (Side Income)';
      case FounderGoal.SERVICE:
        return 'Cung cấp dịch vụ (Agency/Service)';
      case FounderGoal.PRODUCT:
        return 'Sản phẩm hoàn chỉnh (Product)';
      case FounderGoal.LEARN:
        return 'Học hỏi & Khám phá (Learn)';
    }
  }

  String _goalSubtitle(FounderGoal g) {
    switch (g) {
      case FounderGoal.EXPERIMENT:
        return 'Kiểm chứng giả thuyết nhanh với chi phí tối thiểu';
      case FounderGoal.SIDE_INCOME:
        return 'Xây dựng dòng tiền phụ vững chắc';
      case FounderGoal.SERVICE:
        return 'Bán kỹ năng/giải pháp cho khách hàng doanh nghiệp';
      case FounderGoal.PRODUCT:
        return 'Phát triển MVP và tìm Product-Market Fit';
      case FounderGoal.LEARN:
        return 'Học quy trình vận hành One-Person Enterprise';
    }
  }
}
