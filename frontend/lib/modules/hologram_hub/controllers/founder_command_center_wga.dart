part of 'founder_command_center_controller.dart';

// Luồng WGA (mục tiêu tuần → kế hoạch → giao việc) tách khỏi controller chính
// (review 2026-09-27, G-11). Cùng library nên dùng được state private.
extension FounderCommandCenterWga on FounderCommandCenterController {
  // ── WGA: Weekly Goal → Agent Execution ──────────────────────────────────

  /// Tải danh sách kế hoạch triển khai (draft) của dự án active.
  Future<void> loadDraftPlans() async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      draftPlans.clear();
      return;
    }
    try {
      final res = await _executionPlanService.listDraftPlansWithDecomposition(pid);
      draftPlans.assignAll(res.plans);
      latestDecomposition.value = res.decomposition;
    } catch (e) {
      debugPrint('[FounderCommandCenter] loadDraftPlans error: $e');
    }
  }

  Future<void> loadFounderInbox() async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      founderInboxTasks.clear();
      return;
    }
    try {
      founderInboxTasks.assignAll(await _executionPlanService.listFounderInbox());
    } catch (e) {
      debugPrint('[FounderCommandCenter] loadFounderInbox error: $e');
    }
  }

  /// WGA G10 — founder bấm "Lập kế hoạch & giao việc" trong chat: nội dung ô
  /// nhập là mục tiêu, gửi thẳng tới luồng phân rã (origin=chat, conversation
  /// hiện tại) thay vì chờ bộ đoán ý định `goal_confirm`.
  Future<void> planFromChatInput() async {
    final text = chatInputController.text.trim();
    if (text.isEmpty) {
      AppToast.warning('Nhập mục tiêu cần lập kế hoạch vào ô chat trước.');
      return;
    }
    chatInputController.clear();
    await requestDecomposition(text, origin: 'chat');
  }

  /// Founder đặt/sửa mục tiêu tuần và nhờ agent lập kế hoạch triển khai.
  Future<void> requestDecomposition(
    String focus, {
    String origin = 'command_center',
    String? originRef,
  }) async {
    final pid = activeProjectId.value;
    if (pid == null || pid.isEmpty) {
      AppToast.warning('Chưa có dự án active để đặt mục tiêu.');
      return;
    }
    if (focus.trim().isEmpty) {
      AppToast.warning('Mục tiêu tuần không được để trống.');
      return;
    }
    isDecomposing.value = true;
    // Mục tiêu xác nhận từ chat phải mang conversation gốc — backend dùng nó để
    // báo kết quả lập kế hoạch và tiến độ task về đúng cuộc chat (WGA G9).
    final effectiveOriginRef =
        originRef ?? (origin == 'chat' ? _cofounderConversationId : null);
    try {
      final weeklyPlanId = await _executionPlanService.setWeeklyGoal(
        pid,
        focus.trim(),
        triggerDecomposition: true,
        origin: origin,
        originRef: effectiveOriginRef,
      );
      if (weeklyPlanId != null) {
        latestDecomposition.value =
            DecompositionState(weeklyPlanId: weeklyPlanId, status: 'pending');
      }
      if (effectiveOriginRef != null) _ensureAgentMessageWatch();
      AppToast.info(
        'Đã ghi mục tiêu tuần. AI đang lập kế hoạch triển khai — kế hoạch sẽ hiện ở đây trong giây lát.',
      );
      unawaited(_burstReloadDraftPlans());
    } catch (e) {
      AppToast.error('Không thể đặt mục tiêu: $e');
    } finally {
      isDecomposing.value = false;
    }
  }

  /// Kế hoạch được tạo bất đồng bộ ở backend (event → worker) — reload nhanh
  /// vài nhịp để founder thấy kế hoạch ngay thay vì chờ nhịp poll 20s. (bỏ qua
  /// trong test để không rò future delayed.)
  Future<void> _burstReloadDraftPlans() async {
    if (Get.testMode) return;
    for (final s in const [3, 8, 15]) {
      await Future<void>.delayed(Duration(seconds: s));
      if (draftPlans.isNotEmpty) return;
      await loadDraftPlans();
      if (_surfaceDecompositionFailure()) return;
    }
  }

  /// G6 — phân rã thất bại thì dừng chờ và báo lỗi theo mã (không lỗi thô).
  /// Trả true khi đã báo.
  bool _surfaceDecompositionFailure() {
    final st = latestDecomposition.value;
    if (st == null || !st.isFailed) return false;
    AppToast.error(st.userMessage);
    return true;
  }

  Future<void> acceptPlan(String planId) async {
    final snapshot = List<ExecutionPlan>.from(draftPlans);
    draftPlans.removeWhere((p) => p.id == planId); // optimistic
    try {
      await _executionPlanService.acceptPlan(planId);
      AppToast.success('Đã duyệt kế hoạch. Các việc đã được tạo cho AI và cho bạn.');
      await loadDraftPlans();
    } catch (e) {
      draftPlans.assignAll(snapshot); // rollback
      AppToast.error('Không thể duyệt kế hoạch: $e');
    }
  }

  Future<void> rejectPlan(String planId) async {
    final snapshot = List<ExecutionPlan>.from(draftPlans);
    draftPlans.removeWhere((p) => p.id == planId);
    try {
      await _executionPlanService.rejectPlan(planId);
      AppToast.info('Đã bỏ kế hoạch đề xuất.');
    } catch (e) {
      draftPlans.assignAll(snapshot);
      AppToast.error('Không thể bỏ kế hoạch: $e');
    }
  }

  /// Sửa 1 item của kế hoạch (đổi class / bỏ). Reload để phản ánh guard phía backend.
  Future<void> updatePlanItem(
    String planId,
    String itemId, {
    AutonomyClass? autonomyClass,
    bool? drop,
    String? title,
  }) async {
    try {
      await _executionPlanService.updateItem(
        planId,
        itemId,
        autonomyClass: autonomyClass,
        drop: drop,
        title: title,
      );
      await loadDraftPlans();
    } catch (e) {
      AppToast.error('Không cập nhật được: $e');
      await loadDraftPlans();
    }
  }
}
