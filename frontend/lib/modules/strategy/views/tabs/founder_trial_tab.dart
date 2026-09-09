import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/network/api_result.dart';
import '../../../../core/services/workspace_capability_manifest_controller.dart';
import '../../controllers/strategy_controller.dart';
import '../../founder_trial/founder_trial_board_models.dart';
import '../../founder_trial/founder_trial_board_service.dart';
import '../../founder_trial/founder_trial_board_view.dart';
import '../../services/project_operating_setup_service.dart';

/// Tab "Founder Trial" trong StrategyView (thay ValidationStudioTab).
/// Vòng lặp có dữ liệu thật: Operating Cycle → Assumptions → Experiments →
/// Evidence → Decision, mỗi section theo `surfaceStatus` server-owned.
class FounderTrialTab extends StatefulWidget {
  const FounderTrialTab({super.key});

  @override
  State<FounderTrialTab> createState() => _FounderTrialTabState();
}

class _FounderTrialTabState extends State<FounderTrialTab> {
  final _boardService = FounderTrialBoardService();
  final _setupService = ProjectOperatingSetupService();
  late final WorkspaceCapabilityManifestController _manifest;
  late final StrategyController _strategy;

  bool _loading = true;
  String? _error;
  FounderTrialBoard? _board;
  String? _projectId;

  @override
  void initState() {
    super.initState();
    _manifest = Get.isRegistered<WorkspaceCapabilityManifestController>()
        ? Get.find<WorkspaceCapabilityManifestController>()
        : Get.put(WorkspaceCapabilityManifestController());
    _strategy = Get.isRegistered<StrategyController>()
        ? Get.find<StrategyController>()
        : Get.put(StrategyController());
    _bootstrap();
  }

  String? _resolveProjectId() {
    final active = _strategy.activeProjectId.value;
    if (active != null && active.isNotEmpty) return active;
    final list = _strategy.projects;
    if (list.isEmpty) return null;
    return list.first['id']?.toString();
  }

  Future<void> _bootstrap() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    if (!_manifest.hasLoadedSnapshot.value) {
      await _manifest.reload();
    }
    _projectId = _resolveProjectId();
    if (_projectId == null) {
      setState(() {
        _loading = false;
        _error = 'Chưa có project nào để hiển thị Founder Trial.';
      });
      return;
    }
    await _loadBoard();
  }

  Future<void> _loadBoard() async {
    final pid = _projectId;
    if (pid == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await _boardService.fetch(pid);
    if (!mounted) return;
    switch (res) {
      case ApiSuccess<FounderTrialBoard>(:final data):
        setState(() {
          _board = data;
          _loading = false;
        });
      case ApiFailure<FounderTrialBoard>(:final failure):
        setState(() {
          _error = failure.message;
          _loading = false;
        });
    }
  }

  Future<void> _setCycleDuration(int weeks) async {
    final pid = _projectId;
    if (pid == null) return;
    try {
      await _setupService.updateCycleDuration(pid, weeks);
      await _loadBoard();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Không đổi được độ dài chu kỳ: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _board == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            const SizedBox(height: 8),
            FilledButton.tonal(onPressed: _bootstrap, child: const Text('Thử lại')),
          ],
        ),
      );
    }
    final board = _board!;
    return Column(
      children: [
        if (_strategy.projects.length > 1)
          Padding(
            padding: const EdgeInsets.all(8),
            child: DropdownButton<String>(
              value: _projectId,
              isExpanded: true,
              items: [
                for (final p in _strategy.projects)
                  DropdownMenuItem(
                    value: p['id']?.toString(),
                    child: Text(p['title']?.toString() ?? p['id']?.toString() ?? '—'),
                  ),
              ],
              onChanged: (v) {
                if (v != null && v != _projectId) {
                  setState(() => _projectId = v);
                  _loadBoard();
                }
              },
            ),
          ),
        Expanded(
          child: FounderTrialBoardView(
            board: board,
            manifest: _manifest,
            onRetry: _loadBoard,
            onSetCycleDuration: _setCycleDuration,
          ),
        ),
      ],
    );
  }
}
