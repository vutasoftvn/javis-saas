import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/executive_advisory_board_controller.dart';
import '../models/executive_advisory_board.dart';

class ExecutiveAdvisoryBoardView extends StatelessWidget {
  final String projectId;
  final ExecutiveAdvisoryBoardController controller;

  ExecutiveAdvisoryBoardView({
    super.key,
    required this.projectId,
    ExecutiveAdvisoryBoardController? controller,
  }) : controller = controller ??
            (Get.isRegistered<ExecutiveAdvisoryBoardController>()
                ? Get.find<ExecutiveAdvisoryBoardController>()
                : Get.put(ExecutiveAdvisoryBoardController()));

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0F172A), // Slate 900
      child: Obx(() {
        if (controller.isLoading.value) {
          return const Center(
            child: CircularProgressIndicator(color: Colors.indigoAccent),
          );
        }

        return SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context),
              const SizedBox(height: 24),
              if (controller.errorMessage.value != null) ...[
                _buildErrorBanner(controller.errorMessage.value!),
                const SizedBox(height: 16),
              ],
              _buildActiveDeliberationSection(context),
              const SizedBox(height: 32),
              _buildRolesSection(context),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 16,
      runSpacing: 16,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Hội đồng Cố vấn Điều hành',
              style: TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.bold,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Cố vấn chiến lược cấp L1 (Read/Propose) theo từng Project',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 14,
              ),
            ),
          ],
        ),
        Wrap(
          spacing: 12,
          runSpacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: () => _showPresetDialog(context),
              icon: const Icon(Icons.tune, size: 16, color: Colors.indigoAccent),
              label: const Text(
                'Chọn Preset',
                style: TextStyle(color: Colors.indigoAccent),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.indigoAccent),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            ElevatedButton.icon(
              onPressed: () => _showCreateDeliberationDialog(context),
              icon: const Icon(Icons.add, size: 16, color: Colors.white),
              label: const Text('Tạo Phiên Nghị sự'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.indigoAccent,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildErrorBanner(String message) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.redAccent.withValues(alpha: 0.15),
        border: Border.all(color: Colors.redAccent.withValues(alpha: 0.5)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Colors.redAccent, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveDeliberationSection(BuildContext context) {
    final delib = controller.currentDeliberation.value;
    if (delib == null) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B), // Slate 800
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.gavel, color: Colors.amberAccent, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    delib.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              _buildStateChip(delib.state),
            ],
          ),
          if (delib.activeFrame != null) ...[
            const SizedBox(height: 12),
            Text(
              delib.activeFrame!['question']?.toString() ?? '',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.9),
                fontSize: 14,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
          if (delib.analyses.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Text(
              'Ý kiến từ Cố vấn:',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            ...delib.analyses.map((a) => _buildAnalysisRow(a)),
          ],
          if (delib.state == 'AWAITING_FOUNDER') ...[
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => controller.cancelDeliberation(
                    projectId: projectId,
                    deliberationId: delib.id,
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.redAccent,
                    side: const BorderSide(color: Colors.redAccent),
                  ),
                  child: const Text('Huỷ bỏ'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () => controller.appendDecision(
                    projectId: projectId,
                    deliberationId: delib.id,
                    decisionType: 'APPROVE',
                  ),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  child: const Text('Phê duyệt (Approve)'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAnalysisRow(DeliberationAnalysis analysis) {
    final conclusion = analysis.descriptor['conclusion']?.toString() ?? 'Đã hoàn tất phân tích';
    final confidence = analysis.descriptor['confidence']?.toString() ?? 'UNKNOWN';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.indigoAccent.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              analysis.roleKey.toUpperCase(),
              style: const TextStyle(
                color: Colors.indigoAccent,
                fontSize: 11,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  conclusion,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
                const SizedBox(height: 4),
                Text(
                  'Độ tin cậy: $confidence',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRolesSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Thành phần Ban Cố vấn',
          style: TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final crossAxisCount = constraints.maxWidth > 900 ? 3 : (constraints.maxWidth > 600 ? 2 : 1);
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.4,
              ),
              itemCount: controller.roles.length,
              itemBuilder: (context, index) {
                final role = controller.roles[index];
                return _buildRoleCard(context, role);
              },
            );
          },
        ),
      ],
    );
  }

  Widget _buildRoleCard(BuildContext context, ExecutiveAdvisorRole role) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: role.activationState == ExecutiveActivationState.active
              ? Colors.indigoAccent.withValues(alpha: 0.4)
              : Colors.white.withValues(alpha: 0.06),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  role.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              _buildRoleBadge(role.activationState),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            role.domain,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.5),
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: Text(
              role.description,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontSize: 12,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (role.disabledReason != null) ...[
            Text(
              role.disabledReason!,
              style: const TextStyle(color: Colors.amberAccent, fontSize: 11),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
          ],
          _buildActionRow(role),
        ],
      ),
    );
  }

  Widget _buildRoleBadge(ExecutiveActivationState state) {
    String text;
    Color color;
    switch (state) {
      case ExecutiveActivationState.active:
        text = 'Đang hoạt động';
        color = Colors.green;
        break;
      case ExecutiveActivationState.availableNotActivated:
        text = 'Chưa kích hoạt';
        color = Colors.amber;
        break;
      case ExecutiveActivationState.disabled:
        text = 'Đã dừng';
        color = Colors.grey;
        break;
      case ExecutiveActivationState.unavailable:
        text = 'Chưa sẵn sàng';
        color = Colors.redAccent;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        text,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildActionRow(ExecutiveAdvisorRole role) {
    if (role.activationState == ExecutiveActivationState.availableNotActivated) {
      return SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: () => controller.activateRole(
            projectId: projectId,
            roleKey: role.roleKey,
            expectedVersion: role.assignmentVersion ?? 1,
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.indigoAccent,
            padding: const EdgeInsets.symmetric(vertical: 8),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          ),
          child: const Text('Kích hoạt', style: TextStyle(fontSize: 12)),
        ),
      );
    } else if (role.activationState == ExecutiveActivationState.active) {
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: () => controller.disableRole(
            projectId: projectId,
            roleKey: role.roleKey,
            expectedVersion: role.assignmentVersion ?? 1,
          ),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white70,
            side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
            padding: const EdgeInsets.symmetric(vertical: 8),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          ),
          child: const Text('Tạm dừng', style: TextStyle(fontSize: 12)),
        ),
      );
    }

    // Khi UNAVAILABLE hoặc DISABLED: không hiển thị nút Kích hoạt!
    return const SizedBox(height: 32);
  }

  Widget _buildStateChip(String state) {
    Color color = Colors.blueAccent;
    if (state == 'AWAITING_FOUNDER') color = Colors.amberAccent;
    if (state == 'DECIDED') color = Colors.greenAccent;
    if (state == 'CANCELLED') color = Colors.redAccent;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        state,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold),
      ),
    );
  }

  void _showPresetDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Chọn Startup Core Preset', style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('Giai đoạn Khám phá (Discovery)', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Kích hoạt CFO, CMO (read/propose)', style: TextStyle(color: Colors.white54)),
              onTap: () {
                Navigator.pop(ctx);
                controller.selectStartupPreset(projectId, 'startup-discovery');
              },
            ),
            ListTile(
              title: const Text('Giai đoạn Xây dựng & Ra mắt (Build & Launch)', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Kích hoạt CFO, CMO, COO (read/propose)', style: TextStyle(color: Colors.white54)),
              onTap: () {
                Navigator.pop(ctx);
                controller.selectStartupPreset(projectId, 'startup-build-launch');
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showCreateDeliberationDialog(BuildContext context) {
    final titleController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Tạo Phiên Nghị sự Mới', style: TextStyle(color: Colors.white)),
        content: TextField(
          controller: titleController,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            labelText: 'Chủ đề / Vấn đề cần tham vấn',
            labelStyle: TextStyle(color: Colors.white60),
            hintText: 'VD: Kế hoạch phân bổ vốn Q3',
            hintStyle: TextStyle(color: Colors.white30),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Huỷ', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            onPressed: () {
              final title = titleController.text.trim();
              if (title.isNotEmpty) {
                Navigator.pop(ctx);
                controller.createDraft(projectId: projectId, title: title);
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.indigoAccent),
            child: const Text('Tạo'),
          ),
        ],
      ),
    );
  }
}
