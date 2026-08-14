import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/mission_control_controller.dart';

class MissionControlView extends GetView<MissionControlController> {
  const MissionControlView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F141C),
      appBar: AppBar(
        backgroundColor: const Color(0xFF141C28),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF00E5FF).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.hub_outlined, color: Color(0xFF00E5FF), size: 20),
            ),
            const SizedBox(width: 12),
            const Text(
              'MISSION CONTROL // CHIEF OF STAFF',
              style: TextStyle(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white70),
            onPressed: () => controller.loadApprovals(),
          ),
        ],
      ),
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Left Panel: Mission Dispatcher & Timeline
          Expanded(
            flex: 5,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildMissionInput(context),
                  const SizedBox(height: 16),
                  _buildAgentClusterHUD(),
                  const SizedBox(height: 16),
                  _buildDiagnosisAndPlan(),
                ],
              ),
            ),
          ),
          // Right Panel: Pending Approvals & Live Stream
          Expanded(
            flex: 4,
            child: Container(
              decoration: const BoxDecoration(
                border: Border(left: BorderSide(color: Color(0xFF1E293B), width: 1)),
              ),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildApprovalsSection(),
                  const SizedBox(height: 20),
                  _buildLiveEventStream(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMissionInput(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF16202E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF243447)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'DIRECTIVE / FOUNDER GOAL',
            style: TextStyle(color: Color(0xFF00E5FF), fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.1),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: controller.goalInputController,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            decoration: InputDecoration(
              hintText: 'Nhập mục tiêu (ví dụ: Doanh thu đang giảm. Phân tích sales và tài chính để đề xuất kế hoạch...)',
              hintStyle: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 13),
              filled: true,
              fillColor: const Color(0xFF0B1017),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Obx(() => ElevatedButton.icon(
                    onPressed: controller.isOrchestrating.value ? null : () => controller.runMission(),
                    icon: controller.isOrchestrating.value
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.rocket_launch, size: 16),
                    label: Text(
                      controller.isOrchestrating.value ? 'COORDINATING AGENTS...' : 'LAUNCH MISSION',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, letterSpacing: 1),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00E5FF),
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  )),
              const SizedBox(width: 12),
              OutlinedButton(
                onPressed: () => controller.runMission(
                  customGoal: 'Đánh giá đường ống bán hàng và tình hình tài chính quý 3/2026',
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF94A3B8),
                  side: const BorderSide(color: Color(0xFF243447)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('Preset: Pipeline & Cashflow Q3', style: TextStyle(fontSize: 12)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAgentClusterHUD() {
    return Row(
      children: [
        Expanded(child: _buildAgentCard('Chief of Staff', 'ORCHESTRATOR', const Color(0xFF00E5FF), Icons.psychology)),
        const SizedBox(width: 12),
        Expanded(child: _buildAgentCard('Sales Specialist', 'CRM & PIPELINE', const Color(0xFF10B981), Icons.trending_up)),
        const SizedBox(width: 12),
        Expanded(child: _buildAgentCard('Finance Specialist', 'CASHFLOW & RUNWAY', const Color(0xFFF59E0B), Icons.account_balance)),
      ],
    );
  }

  Widget _buildAgentCard(String title, String role, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF16202E),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(role, style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold, letterSpacing: 0.8)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiagnosisAndPlan() {
    return Obx(() {
      final mission = controller.currentMission.value;
      if (mission == null) {
        return Container(
          padding: const EdgeInsets.all(32),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: const Color(0xFF16202E).withOpacity(0.5),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF243447).withOpacity(0.5)),
          ),
          child: Column(
            children: [
              Icon(Icons.radar, color: Colors.white.withOpacity(0.2), size: 40),
              const SizedBox(height: 12),
              Text(
                'Sẵn sàng điều phối các tác tử nghiệp vụ. Nhập mục tiêu để bắt đầu.',
                style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 13),
              ),
            ],
          ),
        );
      }

      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF16202E),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFF243447)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics_outlined, color: Color(0xFF00E5FF), size: 18),
                const SizedBox(width: 8),
                const Text(
                  'CHIEF OF STAFF SYNTHESIS & 4-WEEK ROADMAP',
                  style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.1),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Text('MISSION COMPLETED', style: TextStyle(color: Color(0xFF10B981), fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              mission.diagnosis,
              style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13, height: 1.5),
            ),
            const Divider(color: Color(0xFF243447), height: 24),
            const Text(
              'ACTION PLAN (4-WEEK EXECUTION)',
              style: TextStyle(color: Color(0xFF00E5FF), fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1),
            ),
            const SizedBox(height: 8),
            ...mission.actionPlan.map((plan) {
              final week = plan['week'] ?? '';
              final tactic = plan['tactic'] ?? '';
              final owner = plan['owner'] ?? '';
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF0B1017),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00E5FF).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text('W$week', style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(child: Text(tactic, style: const TextStyle(color: Colors.white, fontSize: 12))),
                    Text(owner, style: const TextStyle(color: Color(0xFF64748B), fontSize: 11)),
                  ],
                ),
              );
            }).toList(),
          ],
        ),
      );
    });
  }

  Widget _buildApprovalsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.gavel, color: Color(0xFFF59E0B), size: 18),
            const SizedBox(width: 8),
            const Text(
              'APPROVAL GATES',
              style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.1),
            ),
            const Spacer(),
            Obx(() => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF59E0B).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '${controller.pendingApprovals.length} PENDING',
                    style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                )),
          ],
        ),
        const SizedBox(height: 10),
        Obx(() {
          if (controller.pendingApprovals.isEmpty) {
            return Container(
              padding: const EdgeInsets.all(16),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: const Color(0xFF16202E),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text('Không có phê duyệt nào đang chờ.', style: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 12)),
            );
          }

          return Column(
            children: controller.pendingApprovals.map((item) {
              final id = (item['id'] ?? '').toString();
              final tool = (item['tool_name'] ?? '').toString();
              final agent = (item['requested_by_agent'] ?? '').toString();
              final risk = (item['risk_level'] ?? 'medium').toString();

              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF16202E),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFF59E0B).withOpacity(0.4)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(agent, style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 11, fontWeight: FontWeight.bold)),
                        const SizedBox(width: 8),
                        Text(tool, style: const TextStyle(color: Colors.white, fontSize: 12)),
                        const Spacer(),
                        Text(risk.toUpperCase(), style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 10, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () => controller.reject(id),
                          child: const Text('Từ chối', style: TextStyle(color: Colors.redAccent, fontSize: 12)),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          onPressed: () => controller.approve(id),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF10B981),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          ),
                          child: const Text('Phê duyệt', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }).toList(),
          );
        }),
      ],
    );
  }

  Widget _buildLiveEventStream() {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.stream, color: Color(0xFF00E5FF), size: 18),
              const SizedBox(width: 8),
              const Text(
                'LIVE EVENT STREAM',
                style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Expanded(
            child: Obx(() => ListView.builder(
                  itemCount: controller.events.length,
                  itemBuilder: (context, index) {
                    final ev = controller.events[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 6),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0B1017),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(color: Color(0xFF00E5FF), shape: BoxShape.circle),
                          ),
                          const SizedBox(width: 10),
                          Text(ev.eventType, style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 11, fontWeight: FontWeight.bold)),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              ev.data.toString(),
                              style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 11),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                )),
          ),
        ],
      ),
    );
  }
}
