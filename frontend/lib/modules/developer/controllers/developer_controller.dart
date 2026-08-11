import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/developer_service.dart';
import '../../../core/network/realtime_service.dart';

class DeveloperController extends GetxController {
  final DeveloperService _developerService = DeveloperService();
  final RealtimeService _realtimeService = RealtimeService();

  final isLoading = false.obs;
  final devices = <Map<String, dynamic>>[].obs;
  final jobs = <Map<String, dynamic>>[].obs;
  final selectedJob = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    loadDeveloperData();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  @override
  void onClose() {
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    // 'system.connected' fires on every (re)connect, including reconnects
    // after a dropped network - refetch then so state reconciles against the
    // durable tables instead of staying stale from before the drop.
    if (eventType.startsWith('job.') ||
        eventType.startsWith('device.') ||
        eventType == 'system.connected') {
      loadDeveloperData();
    }
  }

  Future<void> loadDeveloperData() async {
    isLoading.value = true;
    try {
      final devList = await _developerService.getDevices();
      devices.value = devList.cast<Map<String, dynamic>>();

      final jobList = await _developerService.getJobs();
      jobs.value = jobList.cast<Map<String, dynamic>>();

      if (jobs.isNotEmpty && selectedJob.value == null) {
        selectedJob.value = jobs.first;
      }
    } catch (e) {
      debugPrint('Error loading developer data: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> createDevJob(String title) async {
    if (title.trim().isEmpty) return;
    final res = await _developerService.createJob({
      'title': title.trim(),
      'required_capabilities': ['claude_code', 'git', 'filesystem']
    });
    if (res != null) {
      Get.snackbar(
        'Đã tạo Job',
        'Tác vụ lập trình đã được đưa vào hàng đợi điều phối',
        backgroundColor: const Color(0xFF00F0FF).withValues(alpha: 0.15),
        colorText: const Color(0xFF00F0FF),
      );
      await loadDeveloperData();
    }
  }

  // Intentionally does not call the backend: submitting job results is a
  // Local Worker Plane action (authenticated as the device, not this human
  // session - see developer_service.dart's note), and no real worker exists
  // yet to have produced a diff worth merging. Faking a "merged" result here
  // would write a false SUCCEEDED status into developer_jobs. Once
  // `desktop_worker/` exists and a job genuinely reaches WAITING_APPROVAL,
  // this becomes a real human-approval endpoint call instead.
  void approveAndMerge(String jobId) {
    Get.snackbar(
      'Chưa khả dụng',
      'Merge tự động cần Local Worker Plane (desktop_worker), phần này chưa được triển khai. '
      'Job sẽ tự cập nhật khi có một máy trạm thật xử lý và nộp kết quả.',
      backgroundColor: const Color(0xFFF59E0B).withValues(alpha: 0.2),
      colorText: const Color(0xFFF59E0B),
    );
  }
}
