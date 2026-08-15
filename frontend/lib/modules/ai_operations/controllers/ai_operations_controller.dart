import 'package:get/get.dart';
import '../../../data/services/execution_service.dart';

class AiOperationsController extends GetxController {
  final ExecutionService _service;

  AiOperationsController({ExecutionService? service})
      : _service = service ?? ExecutionService();

  final isLoading = false.obs;
  final isDetailsLoading = false.obs;
  final currentTab = 0.obs; // 0: Jobs, 1: Artifacts, 2: Health
  final selectedStatusFilter = 'all'.obs;

  final jobs = <Map<String, dynamic>>[].obs;
  final selectedJob = Rxn<Map<String, dynamic>>();
  final selectedJobArtifacts = <Map<String, dynamic>>[].obs;
  final allArtifacts = <Map<String, dynamic>>[].obs;
  final health = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  Future<void> loadAll() async {
    isLoading.value = true;
    try {
      await Future.wait([
        loadJobs(),
        loadHealth(),
      ]);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> loadJobs() async {
    final status = selectedStatusFilter.value == 'all' ? null : selectedStatusFilter.value;
    final list = await _service.getJobs(status: status);
    jobs.assignAll(list.map((e) => Map<String, dynamic>.from(e as Map)).toList());

    // Populate allArtifacts from completed jobs
    final artifactsList = <Map<String, dynamic>>[];
    for (final j in jobs) {
      final arts = j['artifacts'];
      if (arts is List) {
        for (final a in arts) {
          if (a is Map) {
            final artMap = Map<String, dynamic>.from(a);
            artMap['job_id'] = j['id_str'] ?? j['id']?.toString() ?? '';
            artMap['agent_key'] = j['agent_key'] ?? '';
            artifactsList.add(artMap);
          }
        }
      }
    }
    allArtifacts.assignAll(artifactsList);
  }

  Future<void> selectJob(Map<String, dynamic> job) async {
    selectedJob.value = job;
    final jobId = job['id_str'] ?? job['id']?.toString();
    if (jobId != null && jobId.isNotEmpty) {
      isDetailsLoading.value = true;
      try {
        final detailed = await _service.getJob(jobId);
        if (detailed != null) {
          selectedJob.value = detailed;
        }
        final arts = await _service.getArtifacts(jobId);
        selectedJobArtifacts.assignAll(
          arts.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
        );
      } finally {
        isDetailsLoading.value = false;
      }
    }
  }

  Future<void> loadHealth() async {
    final res = await _service.getHealth();
    if (res != null) {
      health.value = res;
    }
  }

  void setFilter(String status) {
    selectedStatusFilter.value = status;
    loadJobs();
  }

  void setTab(int index) {
    currentTab.value = index;
  }
}
