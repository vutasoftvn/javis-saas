import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/audit_service.dart';
import '../../../core/network/realtime_service.dart';

class AuditController extends GetxController {
  final AuditService _auditService = AuditService();
  final RealtimeService _realtimeService = RealtimeService();

  final isLoading = false.obs;
  final events = <Map<String, dynamic>>[].obs;
  final totalCount = 0.obs;
  final selectedAction = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadAuditEvents();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  @override
  void onClose() {
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    // 'audit.*' covers every write_audit_log() call site (approvals,
    // outcomes, artifacts, ...); 'system.connected' fires on every
    // (re)connect so a dropped-network reconnect reconciles against
    // audit_logs instead of showing whatever was loaded before the drop.
    if (eventType.startsWith('audit.') || eventType == 'system.connected') {
      loadAuditEvents();
    }
  }

  Future<void> loadAuditEvents() async {
    isLoading.value = true;
    try {
      final res = await _auditService.getAuditEvents(
        action: selectedAction.value.isNotEmpty ? selectedAction.value : null,
      );
      totalCount.value = res['total'] as int? ?? 0;
      final rawEvents = res['events'] as List<dynamic>? ?? [];
      events.value = rawEvents.cast<Map<String, dynamic>>();
    } catch (e) {
      debugPrint('Error loading audit events: $e');
    } finally {
      isLoading.value = false;
    }
  }

  void filterByAction(String action) {
    if (selectedAction.value == action) {
      selectedAction.value = '';
    } else {
      selectedAction.value = action;
    }
    loadAuditEvents();
  }
}
