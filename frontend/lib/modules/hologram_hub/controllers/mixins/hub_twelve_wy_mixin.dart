import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/session/session_controller.dart';
import '../../../../data/models/twelve_wy_model.dart';
import '../../../../modules/strategy/services/twelve_wy_service.dart';

mixin HubTwelveWyMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  TwelveWyService get twelveWyService;
  int? get selectedProjectIdValue;

  // Fix (2026-09-02, epoch-guard full audit) — xem chú thích tại
  // `HubControlPlaneMixin._workspaceGeneration`: `loadTwelveWyDashboard` gọi
  // API rồi ghi thẳng kết quả (dashboard 12 Tuần — dữ liệu tenant-specific
  // thật) vào Rx state mà không kiểm tra workspace hiện tại còn khớp không.
  int get _workspaceGeneration => Get.isRegistered<SessionController>()
      ? Get.find<SessionController>().workspaceGeneration
      : 0;

  // ── Observables ──────────────────────────────────────────────────────────
  final twelveWyDashboard = Rxn<TwelveWyDashboardModel>();
  final isTwelveWyLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadTwelveWyDashboard({int? projectId}) async {
    final pid = projectId ?? selectedProjectIdValue;
    if (pid == null) return;
    final generation = _workspaceGeneration;
    try {
      isTwelveWyLoading.value = true;
      final dashboard = await twelveWyService.getDashboard(pid);
      if (_workspaceGeneration != generation) return;
      twelveWyDashboard.value = dashboard;
    } catch (e) {
      debugPrint('[HologramHub] loadTwelveWyDashboard error: $e');
    } finally {
      if (_workspaceGeneration == generation) isTwelveWyLoading.value = false;
    }
  }
}
