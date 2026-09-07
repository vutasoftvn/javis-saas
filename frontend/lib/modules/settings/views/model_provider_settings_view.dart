import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/session/session_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../models/settings_models.dart';
import '../services/model_provider_service.dart';

/// Task 4 (plan 2026-09-07-local-first-model-routing) — founder-only UI cho
/// model provider/policy settings (local-first model routing). Cùng convention
/// StatefulWidget + `service` injectable với
/// `WorkspaceOrientationSettingsCard`, và founder-gating (`_checkIsOperator`)
/// với `ModuleVisibilitySettingsCard`.
///
/// Nguyên tắc bảo mật bắt buộc của toàn bộ file này:
///   1. Widget KHÔNG BAO GIỜ đọc lại API key đã submit — server không trả nó
///      về (xem `ModelProviderModel`, không có field đó); form chỉ CLEAR ô
///      nhập sau khi submit thành công, không "hiển thị lại" giá trị nào.
///   2. 1 provider chỉ được gắn nhãn "Khả dụng" (usable) sau khi
///      `ModelProviderService.testConnection()` trả về `ok=true` THẬT SỰ —
///      không bao giờ suy luận từ `credentialConfigured` (đã cấu hình secret
///      không có nghĩa là secret đó còn đúng/còn hiệu lực).
class ModelProviderSettingsView extends StatefulWidget {
  const ModelProviderSettingsView({super.key, this.service});

  final ModelProviderService? service;

  @override
  State<ModelProviderSettingsView> createState() => _ModelProviderSettingsViewState();
}

/// Trạng thái test-connection hiển thị cho 1 profile — tách biệt hẳn khỏi
/// `credentialConfigured` (đã cấu hình secret) để không bao giờ nhầm lẫn 2
/// khái niệm "đã cấu hình" và "đã kiểm tra khả dụng thật".
enum _ConnectionCheckState { untested, checking, usable, failed }

class _ModelProviderSettingsViewState extends State<ModelProviderSettingsView> {
  late final ModelProviderService _service;

  bool _isLoading = true;
  String? _loadError;
  List<ModelProviderModel> _providers = const [];
  ModelPolicyModel? _workspaceDefaultPolicy;

  final Map<String, _ConnectionCheckState> _checkStateByProfile = {};
  final Map<String, String> _checkDetailByProfile = {};

  bool _showAddForm = false;
  bool _isSubmittingProvider = false;
  String? _submitError;

  String _newProviderType = 'deepseek_api';
  final TextEditingController _profileIdController = TextEditingController();
  final TextEditingController _modelIdController = TextEditingController();
  final TextEditingController _apiKeyController = TextEditingController();
  final TextEditingController _baseUrlController = TextEditingController();

  static const _providerTypes = <String>[
    'local_openai_compatible',
    'anthropic_api',
    'openai_api',
    'openrouter_api',
    'deepseek_api',
    'claude_cli',
    'codex_cli',
    'gemini_cli',
  ];

  // Sentinel dùng để đọc/ghi WORKSPACE default (khớp
  // `apps/cosa/api/model_policy_routes.py::WORKSPACE_DEFAULT_SENTINEL`).
  static const _workspaceDefaultKey = '_workspace_default';

  bool _checkIsOperator() {
    if (!Get.isRegistered<SessionController>()) return false;
    final role = Get.find<SessionController>().active.value?.role.toLowerCase() ?? '';
    return role == 'founder' || role == 'co-founder' || role == 'admin' || role == 'owner';
  }

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? ModelProviderService();
    _loadAll();
  }

  @override
  void dispose() {
    _profileIdController.dispose();
    _modelIdController.dispose();
    _apiKeyController.dispose();
    _baseUrlController.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });

    final providersResult = await _service.listProviders();
    final policyResult = await _service.getPolicy(_workspaceDefaultKey);

    if (!mounted) return;
    setState(() {
      _isLoading = false;
      providersResult.when(
        success: (data, _) => _providers = data,
        failure: (failure) => _loadError = failure.message,
      );
      policyResult.when(
        success: (data, _) => _workspaceDefaultPolicy = data,
        failure: (_) => _workspaceDefaultPolicy = null,
      );
    });
  }

  Future<void> _submitNewProvider() async {
    setState(() {
      _isSubmittingProvider = true;
      _submitError = null;
    });

    final result = await _service.createProvider(
      providerType: _newProviderType,
      profileId: _profileIdController.text.trim().isEmpty ? null : _profileIdController.text.trim(),
      modelId: _modelIdController.text.trim().isEmpty ? null : _modelIdController.text.trim(),
      apiKey: _apiKeyController.text.isEmpty ? null : _apiKeyController.text,
      baseUrl: _baseUrlController.text.trim().isEmpty ? null : _baseUrlController.text.trim(),
    );

    if (!mounted) return;
    result.when(
      success: (data, _) {
        setState(() {
          _isSubmittingProvider = false;
          _showAddForm = false;
          // Clear form — KHÔNG bao giờ repopulate API key field từ response
          // (server không trả nó, và kể cả có cũng không được hiển thị lại).
          _profileIdController.clear();
          _modelIdController.clear();
          _apiKeyController.clear();
          _baseUrlController.clear();
          _providers = [..._providers, data];
        });
      },
      failure: (failure) {
        setState(() {
          _isSubmittingProvider = false;
          _submitError = failure.message;
        });
      },
    );
  }

  Future<void> _testConnection(String profileId) async {
    setState(() {
      _checkStateByProfile[profileId] = _ConnectionCheckState.checking;
    });

    final result = await _service.testConnection(profileId);
    if (!mounted) return;

    result.when(
      success: (data, _) {
        setState(() {
          // `data.ok` là NGUỒN DUY NHẤT quyết định "usable" — không suy luận
          // từ `credentialConfigured` hay bất kỳ state cục bộ nào khác.
          _checkStateByProfile[profileId] =
              data.ok ? _ConnectionCheckState.usable : _ConnectionCheckState.failed;
          _checkDetailByProfile[profileId] = data.detail;
        });
      },
      failure: (failure) {
        setState(() {
          _checkStateByProfile[profileId] = _ConnectionCheckState.failed;
          _checkDetailByProfile[profileId] = failure.message;
        });
      },
    );
  }

  Future<void> _setWorkspaceDefault(String primaryProfileId) async {
    final result = await _service.setPolicy(
      _workspaceDefaultKey,
      primaryProfileId: primaryProfileId,
    );
    if (!mounted) return;
    result.when(
      success: (data, _) => setState(() => _workspaceDefaultPolicy = data),
      failure: (failure) => setState(() => _submitError = failure.message),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isOperator = _checkIsOperator();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(isOperator),
          const SizedBox(height: 16),
          const Divider(color: Colors.white10, height: 1),
          const SizedBox(height: 16),
          if (_isLoading)
            const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          else ...[
            if (_loadError != null) _buildErrorBanner(_loadError!),
            _buildPrecedenceSummary(),
            const SizedBox(height: 16),
            _buildProviderList(isOperator),
            if (isOperator) ...[
              const SizedBox(height: 16),
              if (_showAddForm) _buildAddForm() else _buildAddButton(),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildHeader(bool isOperator) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.hub_rounded, color: Color(0xFF3B82F6), size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Model Providers (Local-first)',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 2),
              Text(
                isOperator
                    ? 'Founder quản lý API key/local endpoint và thứ tự ưu tiên model.'
                    : 'Trạng thái model provider của workspace (chỉ đọc).',
                style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: _isLoading ? null : _loadAll,
          icon: const Icon(Icons.refresh_rounded, color: Colors.white54, size: 20),
          tooltip: 'Tải lại',
        ),
      ],
    );
  }

  Widget _buildErrorBanner(String message) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: const TextStyle(color: Colors.red, fontSize: 13))),
        ],
      ),
    );
  }

  Widget _buildPrecedenceSummary() {
    final policy = _workspaceDefaultPolicy;
    if (policy == null) return const SizedBox.shrink();

    return Container(
      key: const ValueKey('model-policy-precedence'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.route_rounded, color: Color(0xFF10B981), size: 18),
              const SizedBox(width: 8),
              const Text(
                'Route đang áp dụng cho workspace',
                style: TextStyle(fontSize: 13, color: Colors.white, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            policy.isSystemDefault
                ? 'System default: ${policy.resolvedProviderType} / ${policy.resolvedModelId}'
                : 'Workspace default: ${policy.resolvedProviderType} / ${policy.resolvedModelId} (profile ${policy.resolvedProfileId})',
            style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
          ),
          if (policy.fallbackProfileIds.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Fallback: ${policy.fallbackProfileIds.join(' → ')}',
                style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildProviderList(bool isOperator) {
    if (_providers.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Text(
          'Chưa có provider nào được cấu hình.',
          style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
        ),
      );
    }

    return Column(
      children: _providers.map((p) => _buildProviderTile(p, isOperator)).toList(),
    );
  }

  Widget _buildProviderTile(ModelProviderModel provider, bool isOperator) {
    final checkState = _checkStateByProfile[provider.profileId] ?? _ConnectionCheckState.untested;
    final checkDetail = _checkDetailByProfile[provider.profileId];

    return Container(
      key: ValueKey('model-provider-${provider.profileId}'),
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${provider.profileId} · ${provider.providerType}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              _buildStatusChip(checkState, provider.credentialConfigured),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'model: ${provider.modelId}${provider.baseUrl != null ? ' · ${provider.baseUrl}' : ''}',
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
          ),
          if (checkDetail != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                checkDetail,
                style: TextStyle(
                  color: checkState == _ConnectionCheckState.usable
                      ? const Color(0xFF10B981)
                      : Colors.red.shade300,
                  fontSize: 11,
                ),
              ),
            ),
          if (isOperator) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                key: ValueKey('model-provider-test-${provider.profileId}'),
                onPressed: checkState == _ConnectionCheckState.checking
                    ? null
                    : () => _testConnection(provider.profileId),
                icon: checkState == _ConnectionCheckState.checking
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.bolt_rounded, size: 14),
                label: const Text('Kiểm tra kết nối', style: TextStyle(fontSize: 12)),
              ),
            ),
            if (provider.status == 'ACTIVE')
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  onPressed: () => _setWorkspaceDefault(provider.profileId),
                  child: const Text(
                    'Đặt làm workspace default',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatusChip(_ConnectionCheckState state, bool credentialConfigured) {
    final (label, color) = switch (state) {
      _ConnectionCheckState.usable => ('Khả dụng (đã kiểm tra)', const Color(0xFF10B981)),
      _ConnectionCheckState.checking => ('Đang kiểm tra...', Colors.amber),
      _ConnectionCheckState.failed => ('Kiểm tra thất bại', Colors.red),
      _ConnectionCheckState.untested => (
          credentialConfigured ? 'Đã cấu hình (chưa kiểm tra)' : 'Chưa cấu hình credential',
          Colors.white38,
        ),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildAddButton() {
    return OutlinedButton.icon(
      onPressed: () => setState(() => _showAddForm = true),
      icon: const Icon(Icons.add_rounded, size: 16),
      label: const Text('Thêm provider'),
    );
  }

  Widget _buildAddForm() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_submitError != null) ...[
            Text(_submitError!, style: const TextStyle(color: Colors.red, fontSize: 12)),
            const SizedBox(height: 8),
          ],
          DropdownButtonFormField<String>(
            key: const ValueKey('model-provider-type-dropdown'),
            initialValue: _newProviderType,
            decoration: const InputDecoration(labelText: 'Provider type'),
            items: _providerTypes
                .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                .toList(),
            onChanged: (v) {
              if (v != null) setState(() => _newProviderType = v);
            },
          ),
          const SizedBox(height: 10),
          TextField(
            key: const ValueKey('model-provider-profile-id-field'),
            controller: _profileIdController,
            decoration: const InputDecoration(labelText: 'Profile ID (tuỳ chọn)'),
          ),
          const SizedBox(height: 10),
          TextField(
            key: const ValueKey('model-provider-model-id-field'),
            controller: _modelIdController,
            decoration: const InputDecoration(labelText: 'Model ID'),
          ),
          const SizedBox(height: 10),
          TextField(
            key: const ValueKey('model-provider-base-url-field'),
            controller: _baseUrlController,
            decoration: const InputDecoration(labelText: 'Base URL (local endpoint, tuỳ chọn)'),
          ),
          const SizedBox(height: 10),
          TextField(
            key: const ValueKey('model-provider-api-key-field'),
            controller: _apiKeyController,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'API key (tuỳ chọn)'),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              ElevatedButton(
                key: const ValueKey('model-provider-submit'),
                onPressed: _isSubmittingProvider ? null : _submitNewProvider,
                child: _isSubmittingProvider
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Lưu provider'),
              ),
              const SizedBox(width: 10),
              TextButton(
                onPressed: () => setState(() => _showAddForm = false),
                child: const Text('Hủy'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
