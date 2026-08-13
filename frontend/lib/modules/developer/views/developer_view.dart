import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/developer_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class DeveloperView extends GetView<DeveloperController> {
  const DeveloperView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<DeveloperController>()) {
      Get.put(DeveloperController());
    }

    final newJobTextController = TextEditingController();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        JavisFloatingAppBar(
              title: 'Bảng điều khiển Lập trình (Developer Hub)',
              subtitle: 'Điều phối tác vụ Claude Code CLI, quản lý Node máy trạm và giám sát Worktree Diffs.',
              icon: Icons.developer_board_rounded,
              actions: [
                ElevatedButton.icon(
                  onPressed: () {
                    _showCreateJobDialog(context, newJobTextController);
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary.withValues(alpha: 0.15),
                    foregroundColor: AppTheme.primary,
                    side: const BorderSide(color: AppTheme.primary),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                  icon: const Icon(Icons.add_rounded, size: 18),
                  label: const Text('Tạo Job mới', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ),
                const SizedBox(width: 10),
                Container(
                  decoration: const BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    tooltip: 'Tải lại',
                    icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                    onPressed: controller.loadDeveloperData,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Main Content 2-Column Split
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value) {
                  return const Center(child: CircularProgressIndicator());
                }

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Left Column: Devices & Jobs Queue
                    Expanded(
                      flex: 5,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildDevicesSection(),
                          const SizedBox(height: 16),
                          const Text(
                            'Hàng đợi Developer Jobs',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                          const SizedBox(height: 10),
                          Expanded(child: _buildJobsList()),
                        ],
                      ),
                    ),
                    const SizedBox(width: 20),

                    // Right Column: Selected Job Inspector
                    Expanded(
                      flex: 6,
                      child: _buildJobInspector(),
                    ),
                  ],
                );
              }),
            ),
          ],
        );
  }

  Widget _buildDevicesSection() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0D172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Mạng lưới Máy trạm (Device Nodes)',
                style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              Text(
                '${controller.devices.length} Nodes',
                style: const TextStyle(fontSize: 12, color: Color(0xFF00F0FF), fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (controller.devices.isEmpty)
            const Text(
              'Chưa có máy trạm nào được kết nối qua `desktop_worker`.',
              style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
            )
          else
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: controller.devices.map((d) {
                  final name = d['name'] as String? ?? 'Device';
                  final platform = d['platform'] as String? ?? 'macos';
                  final isOnline = (d['status'] as String? ?? '') == 'online';

                  return Container(
                    margin: const EdgeInsets.only(right: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF070C18),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: isOnline ? const Color(0xFF10B981) : const Color(0xFF334155)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          platform == 'macos' ? Icons.laptop_mac : Icons.computer,
                          size: 16,
                          color: isOnline ? const Color(0xFF10B981) : Colors.grey,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          name,
                          style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildJobsList() {
    if (controller.jobs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.terminal, size: 48, color: AppTheme.textMutedDark),
            SizedBox(height: 12),
            Text(
              'Chưa có Developer Job nào trong hàng đợi',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: controller.jobs.length,
      itemBuilder: (context, index) {
        final job = controller.jobs[index];
        final isSelected = controller.selectedJob.value?['id'] == job['id'];
        final status = job['status'] as String? ?? 'QUEUED';
        final title = job['title'] as String? ?? 'Developer Task';

        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () => controller.selectedJob.value = job,
              borderRadius: BorderRadius.circular(10),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isSelected ? const Color(0xFF00F0FF).withValues(alpha: 0.1) : const Color(0xFF0D172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isSelected ? const Color(0xFF00F0FF) : const Color(0xFF1E293B),
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600, color: Colors.white),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        status,
                        style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildJobInspector() {
    final job = controller.selectedJob.value;
    if (job == null) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF0D172A),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        child: const Center(
          child: Text('Chọn một job từ hàng đợi để xem chi tiết', style: TextStyle(color: AppTheme.textMutedDark)),
        ),
      );
    }

    final jobId = job['id'] as String? ?? '';
    final title = job['title'] as String? ?? '';
    final status = job['status'] as String? ?? 'QUEUED';
    final diff = job['diff_summary'] as String? ?? 'Chưa có code changes được tạo.';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0D172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  status,
                  style: const TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Job ID: $jobId',
            style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
          ),
          const SizedBox(height: 16),

          const Text(
            'Worktree Diff & Code Changes',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF00F0FF)),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF070C18),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: SingleChildScrollView(
                child: Text(
                  diff,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5, color: Color(0xFFCBD5E1)),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton.icon(
                onPressed: () => controller.approveAndMerge(jobId),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                ),
                icon: const Icon(Icons.check, size: 18),
                label: const Text('Phê duyệt & Merge Code', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showCreateJobDialog(BuildContext context, TextEditingController textCtrl) {
    Get.dialog(
      Dialog(
        backgroundColor: const Color(0xFF0D172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: Color(0xFF1E293B)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Tạo Developer Job Mới',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: textCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  hintText: 'Nhập mô tả task (VD: Fix auth middleware token timeout...)',
                  hintStyle: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 18),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Get.back(),
                    child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () {
                      controller.createDevJob(textCtrl.text);
                      textCtrl.clear();
                      Get.back();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00F0FF),
                      foregroundColor: Colors.black,
                    ),
                    child: const Text('Khởi tạo', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
