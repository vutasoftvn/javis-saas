import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/settings_controller.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/lifecycle/lifecycle_service.dart';
import '../../../core/lifecycle/widgets/lifecycle_settings_section.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../../../core/localization/app_translations.dart';
import 'widgets/ai_gateway_settings_card.dart';
import 'widgets/language_settings_card.dart';
import 'widgets/module_visibility_settings_card.dart';
import 'widgets/workspace_orientation_settings_card.dart';
import 'widgets/permissions_panel.dart';
import 'model_provider_settings_view.dart';

class SettingsView extends GetView<SettingsController> {
  const SettingsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<SettingsController>()) {
      Get.put(SettingsController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CosaFloatingAppBar(
          title: L10nKey.settingsTitle.tr,
          subtitle: L10nKey.settingsSubtitle.tr,
          icon: Icons.settings_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator());
            }
            return SingleChildScrollView(
              padding: const EdgeInsets.only(top: 8, bottom: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: const [
                  LanguageSettingsCard(),
                  SizedBox(height: 12),
                  WorkspaceOrientationSettingsCard(),
                  SizedBox(height: 12),
                  _WorkspaceLifecycleSettingsCard(),
                  SizedBox(height: 12),
                  ModuleVisibilitySettingsCard(),
                  SizedBox(height: 12),
                  AiGatewaySettingsCard(),
                  SizedBox(height: 12),
                  ModelProviderSettingsView(),
                  SizedBox(height: 12),
                  PermissionsPanel(),
                ],
              ),
            );
          }),
        ),
      ],
    );
  }
}

/// Task 13 — bọc `LifecycleSettingsSection` cho Workspace. `SettingsController`
/// hiện là stub (chỉ có `isLoading`), không giữ `lifecycleStage`/`stageVersion`
/// của workspace, và `LifecycleService` (Task 12) cố tình KHÔNG có endpoint
/// GET lifecycle hiện tại (chỉ PATCH transition + GET events lịch sử — xem
/// comment trong lifecycle_service.dart). Vì vậy widget này tự fetch
/// `GET /identity/workspaces/:id` — endpoint CÓ SẴN, đã được
/// `WorkspaceOrientationSettingsCard` gọi ngay phía trên để lấy
/// vision/mission/coreValues — response `Workspace` (workspace.service.ts)
/// vốn đã có sẵn `lifecycleStage` + `stageVersion`, chỉ là frontend chưa parse
/// 2 field đó trước Task 13. Không phải endpoint mới, không phải suy diễn
/// giá trị giả.
class _WorkspaceLifecycleSettingsCard extends StatefulWidget {
  const _WorkspaceLifecycleSettingsCard();

  @override
  State<_WorkspaceLifecycleSettingsCard> createState() =>
      _WorkspaceLifecycleSettingsCardState();
}

class _WorkspaceLifecycleSettingsCardState
    extends State<_WorkspaceLifecycleSettingsCard> {
  String? _workspaceId;
  String? _currentStage;
  int? _currentStageVersion;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final wsId = await SecureStorageService.read('workspace_id');
      if (wsId == null || wsId.isEmpty) {
        setState(() {
          _workspaceId = null;
          _isLoading = false;
        });
        return;
      }
      final res = await ApiClient.get('/identity/workspaces/$wsId');
      if (res.statusCode != 200) {
        throw StateError(
          'Không tải được giai đoạn workspace (HTTP ${res.statusCode}).',
        );
      }
      final body = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
      setState(() {
        _workspaceId = wsId;
        _currentStage = body['lifecycleStage']?.toString();
        _currentStageVersion = body['stageVersion'] is int
            ? body['stageVersion'] as int
            : int.tryParse(body['stageVersion']?.toString() ?? '');
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_errorMessage != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_errorMessage!),
              const SizedBox(height: 8),
              ElevatedButton(onPressed: _load, child: const Text('Thử lại')),
            ],
          ),
        ),
      );
    }
    if (_workspaceId == null || _currentStage == null || _currentStageVersion == null) {
      // Chưa có workspace_id hoặc backend chưa trả đủ lifecycleStage/stageVersion
      // — không hiển thị section thay vì render với giá trị giả.
      return const SizedBox.shrink();
    }
    return LifecycleSettingsSection(
      entityType: LifecycleEntityType.workspace,
      entityId: _workspaceId!,
      currentStage: _currentStage!,
      currentStageVersion: _currentStageVersion!,
    );
  }
}
