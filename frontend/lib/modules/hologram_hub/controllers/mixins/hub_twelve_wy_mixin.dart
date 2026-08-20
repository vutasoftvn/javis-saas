import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/twelve_wy_model.dart';
import '../../../../modules/strategy/services/twelve_wy_service.dart';

mixin HubTwelveWyMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  TwelveWyService get twelveWyService;
  int? get selectedProjectIdValue;

  // ── Observables ──────────────────────────────────────────────────────────
  final twelveWyDashboard = Rxn<TwelveWyDashboardModel>();
  final isTwelveWyLoading = false.obs;

  // ── Methods ──────────────────────────────────────────────────────────────

  Future<void> loadTwelveWyDashboard({int? projectId}) async {
    final pid = projectId ?? selectedProjectIdValue;
    if (pid == null) return;
    try {
      isTwelveWyLoading.value = true;
      twelveWyDashboard.value = await twelveWyService.getDashboard(pid);
    } catch (e) {
      debugPrint('[HologramHub] loadTwelveWyDashboard error: $e');
    } finally {
      isTwelveWyLoading.value = false;
    }
  }
}
