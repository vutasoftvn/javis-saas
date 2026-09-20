import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/shell/chat_panel_controller.dart';
import '../../../data/models/workforce_pack_model.dart';
import '../../agents/controllers/agents_controller.dart';
import '../../agents/views/widgets/agent_card.dart';
import '../../agents/views/widgets/agent_test_run_drawer.dart';
import '../controllers/founder_command_center_controller.dart' show WorkforceLoadState;

class AiWorkforceTab extends StatefulWidget {
  final List<WorkforcePackModel>? packs;
  final Function(String packKey, bool value)? onTogglePack;
  final WorkforceLoadState? loadState;

  const AiWorkforceTab({
    super.key,
    this.packs,
    this.onTogglePack,
    this.loadState,
  });

  @override
  State<AiWorkforceTab> createState() => _AiWorkforceTabState();
}

class _AiWorkforceTabState extends State<AiWorkforceTab> {
  late final AgentsController _agentsController;
  bool _isLocalController = false;

  static const List<String> departments = [
    'All',
    'Operations',
    'Marketing',
    'Sales',
    'Engineering',
    'Finance',
    'Legal',
  ];

  @override
  void initState() {
    super.initState();
    if (Get.isRegistered<AgentsController>()) {
      _agentsController = Get.find<AgentsController>();
    } else {
      _agentsController = Get.put(AgentsController());
      _isLocalController = true;
    }
  }

  @override
  void dispose() {
    if (_isLocalController && Get.isRegistered<AgentsController>()) {
      Get.delete<AgentsController>();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final packs = widget.packs ?? const [];
    final coreDomains = packs.where((p) => p.isCore).toList();
    final hasPackList = packs.isNotEmpty;

    // Khi loadState là unavailable, chỉ hiển thị thông báo trung thực,
    // không hiển thị các CTA đột biến (mutation CTAs) hoặc điều khiển mở rộng.
    if (widget.loadState == WorkforceLoadState.unavailable) {
      return Container(
        padding: const EdgeInsets.all(16),
        margin: const EdgeInsets.only(bottom: 20),
        decoration: BoxDecoration(
          color: const Color(0xFF2A1B1B),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: const Color(0xFFF87171).withValues(alpha: 0.4),
          ),
        ),
        child: const Row(
          children: [
            Icon(Icons.error_outline, color: Color(0xFFF87171), size: 20),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Không tải được danh sách AI Workforce. Vui lòng thử lại sau.',
                style: TextStyle(color: Color(0xFFF87171), fontSize: 13),
              ),
            ),
          ],
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 900;

        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Nếu có packs từ composition API, hiển thị Core Domains count theo dữ liệu thật
              if (hasPackList) ...[
                Row(
                  children: [
                    const Icon(Icons.hub, color: Color(0xFF6366F1), size: 20),
                    const SizedBox(width: 8),
                    Text(
                      coreDomains.isEmpty
                          ? 'CORE DOMAIN WORKFORCE (chưa có dữ liệu phân loại)'
                          : '${coreDomains.length} CORE DOMAIN WORKFORCE (Luôn kích hoạt)',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
              ],

              // 1. Header Banner & Department Filter
              _buildWorkforceHeader(isWide),
              const SizedBox(height: 16),

              // 2. Agents Grid
              _buildAgentsGrid(constraints.maxWidth),

              // 3. Optional Packs Store Section (Nếu có packs)
              if (widget.packs != null && widget.packs!.isNotEmpty) ...[
                const SizedBox(height: 32),
                _buildOptionalPacksSection(isWide),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildWorkforceHeader(bool isWide) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF6366F1).withValues(alpha: 0.3),
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(Icons.groups_rounded, color: Colors.white, size: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'AI WORKFORCE ROSTER & SPECIALISTS',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      'Biệt đội AI chuyên trách các phòng ban vận hành dưới sự chỉ huy của Co-Founder & Founder.',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Colors.white.withValues(alpha: 0.7),
                      ),
                    ),
                  ],
                ),
              ),
              if (isWide)
                ElevatedButton.icon(
                  onPressed: () {
                    if (Get.isRegistered<ChatPanelController>()) {
                      final chat = Get.find<ChatPanelController>();
                      chat.open();
                    }
                  },
                  icon: const Icon(Icons.hub_outlined, size: 16),
                  label: const Text('Hội ý cùng AI Workforce'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6366F1),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 20),
          const Divider(color: Color(0xFF334155), height: 1),
          const SizedBox(height: 16),

          // Department Filter Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Obx(() {
              final currentDept = _agentsController.selectedDepartment.value;
              return Row(
                children: departments.map((dept) {
                  final isSelected = currentDept == dept;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(dept == 'All' ? 'Tất cả phòng ban' : dept),
                      selected: isSelected,
                      onSelected: (_) => _agentsController.filterByDepartment(dept),
                      selectedColor: const Color(0xFF6366F1),
                      backgroundColor: const Color(0xFF0F172A),
                      labelStyle: TextStyle(
                        fontSize: 12,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                        color: isSelected ? Colors.white : Colors.white70,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                        side: BorderSide(
                          color: isSelected ? const Color(0xFF818CF8) : const Color(0xFF334155),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentsGrid(double maxWidth) {
    return Obx(() {
      if (_agentsController.isLoading.value) {
        return const Center(
          child: Padding(
            padding: EdgeInsets.all(48.0),
            child: CircularProgressIndicator(color: Color(0xFF6366F1)),
          ),
        );
      }

      // Danh sách agent từ AgentsController hoặc fallback roster chuẩn của hệ thống COSA
      List<Map<String, dynamic>> agentsList = _agentsController.filteredAgents.toList();

      if (agentsList.isEmpty) {
        // Cung cấp danh sách Agents chuẩn mặc định nếu DB chưa gán riêng cho workspace
        agentsList = _getDefaultCosaAgents(_agentsController.selectedDepartment.value);
      }

      final crossAxisCount = maxWidth >= 1200
          ? 3
          : (maxWidth >= 760 ? 2 : 1);

      return GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: crossAxisCount,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          childAspectRatio: 1.45,
        ),
        itemCount: agentsList.length,
        itemBuilder: (context, index) {
          final agent = agentsList[index];
          return AgentCard(
            agent: agent,
            onTestRun: () => _openTestRunDrawer(context, agent),
            onDetails: () {
              if (Get.isRegistered<ChatPanelController>()) {
                final chat = Get.find<ChatPanelController>();
                chat.open();
              }
            },
          );
        },
      );
    });
  }

  void _openTestRunDrawer(BuildContext context, Map<String, dynamic> agent) {
    _agentsController.openTestRunDrawer(agent);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Align(
          alignment: Alignment.centerRight,
          child: AgentTestRunDrawer(
            agent: agent,
            isLoading: _agentsController.isTestingRun.value,
            result: _agentsController.testRunResult.value,
            onExecute: (prompt, model, temp) {
              _agentsController.executeTestRun(
                prompt,
                model,
                temp,
              );
            },
            onClose: () => Navigator.of(ctx).pop(),
          ),
        );
      },
    );
  }

  List<Map<String, dynamic>> _getDefaultCosaAgents(String filterDept) {
    final all = [
      {
        'id': 'agent_ops',
        'key': 'operations_lead',
        'name': 'Chief of Staff / Ops Lead',
        'role_title': 'Điều phối Vận hành & Phân rã OKR',
        'department': 'Operations',
        'status': 'active',
        'default_model_profile': 'reasoning',
        'risk_level': '2',
      },
      {
        'id': 'agent_mkt',
        'key': 'marketing_specialist',
        'name': 'Growth & Marketing Lead',
        'role_title': 'Nghiên cứu Thị trường & Phễu Chuyển đổi',
        'department': 'Marketing',
        'status': 'active',
        'default_model_profile': 'creative',
        'risk_level': '1',
      },
      {
        'id': 'agent_sales',
        'key': 'sales_rep',
        'name': 'Sales & Customer Pipeline Lead',
        'role_title': 'Xác thực Nỗi đau & Chốt Hợp đồng',
        'department': 'Sales',
        'status': 'active',
        'default_model_profile': 'conversational',
        'risk_level': '2',
      },
      {
        'id': 'agent_tech',
        'key': 'tech_lead',
        'name': 'Architecture & Tech Lead',
        'role_title': 'Thiết kế Hệ thống & Kiểm soát Chất lượng',
        'department': 'Engineering',
        'status': 'active',
        'default_model_profile': 'code_intelligence',
        'risk_level': '3',
      },
      {
        'id': 'agent_fin',
        'key': 'finance_lead',
        'name': 'Finance & Budget Analyst',
        'role_title': 'Kiểm soát Ngân sách, Dòng tiền & Burn Rate',
        'department': 'Finance',
        'status': 'idle',
        'default_model_profile': 'analytical',
        'risk_level': '2',
      },
      {
        'id': 'agent_legal',
        'key': 'legal_compliance',
        'name': 'Legal & Compliance Officer',
        'role_title': 'Rà soát Hợp đồng & Tuân thủ Pháp lý',
        'department': 'Legal',
        'status': 'idle',
        'default_model_profile': 'reasoning',
        'risk_level': '1',
      },
    ];

    if (filterDept == 'All') return all;
    return all.where((a) => a['department'] == filterDept).toList();
  }

  Widget _buildOptionalPacksSection(bool isWide) {
    final packs = widget.packs!;
    final toggle = widget.onTogglePack ?? (_, _) {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.storefront_outlined, color: Color(0xFF10B981), size: 20),
            SizedBox(width: 8),
            Text(
              'OPTIONAL WORKFORCE PACKS (Gói kỹ năng mở rộng)',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.white,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        ...packs.map((p) => Container(
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366F1).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.extension_outlined, color: Color(0xFFA5B4FC), size: 20),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          p.name,
                          style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          p.description ?? '',
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.65), fontSize: 11.5),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: p.isActive,
                    onChanged: (val) => toggle(p.key, val),
                    activeThumbColor: const Color(0xFF10B981),
                    activeTrackColor: const Color(0xFF10B981).withValues(alpha: 0.3),
                    inactiveThumbColor: Colors.white38,
                    inactiveTrackColor: const Color(0xFF334155),
                  ),
                ],
              ),
            )),
      ],
    );
  }
}
