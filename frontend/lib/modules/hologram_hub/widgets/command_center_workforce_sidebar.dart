import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class CommandCenterWorkforceSidebar extends StatefulWidget {
  final bool isCollapsed;
  final VoidCallback onToggleCollapse;
  final Function(Map<String, dynamic> agent) onOpenChat;
  final Function(Map<String, dynamic> agent)? onOpenTestRun;
  final List<Map<String, dynamic>>? customAgents;
  final bool shrinkWrap;

  const CommandCenterWorkforceSidebar({
    super.key,
    required this.isCollapsed,
    required this.onToggleCollapse,
    required this.onOpenChat,
    this.onOpenTestRun,
    this.customAgents,
    this.shrinkWrap = false,
  });

  @override
  State<CommandCenterWorkforceSidebar> createState() =>
      _CommandCenterWorkforceSidebarState();
}

class _CommandCenterWorkforceSidebarState
    extends State<CommandCenterWorkforceSidebar> {
  String _selectedDept = 'All';
  final Set<String> _expandedAgentIds = {'agent_ops_lead'};

  static const List<String> _departments = [
    'All',
    'Operations',
    'Marketing',
    'Sales',
    'Engineering',
    'Finance',
    'Legal',
  ];

  static final List<Map<String, dynamic>> _fallbackAgents = [
    {
      'id': 'agent_ops_lead',
      'key': 'founder_office_orchestrator',
      'name': 'Chief of Staff / Ops Lead',
      'role_title': 'Điều phối Vận hành & Phân rã OKR',
      'department': 'Operations',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 2,
      'status': 'active',
      'enabled': true,
    },
    {
      'id': 'agent_mkt_lead',
      'key': 'campaign_planner',
      'name': 'Growth & Marketing Lead',
      'role_title': 'Nghiên cứu Thị trường & Phễu Chuyển đổi',
      'department': 'Marketing',
      'agent_type': 'specialist',
      'default_model_profile': 'creative',
      'risk_level': 1,
      'status': 'active',
      'enabled': true,
    },
    {
      'id': 'agent_sales_lead',
      'key': 'market_research_specialist',
      'name': 'Sales & Customer Pipeline Lead',
      'role_title': 'Xác thực Nỗi đau & Chốt Hợp đồng B2B',
      'department': 'Sales',
      'agent_type': 'specialist',
      'default_model_profile': 'conversational',
      'risk_level': 2,
      'status': 'active',
      'enabled': true,
    },
    {
      'id': 'agent_tech_lead',
      'key': 'architecture_lead',
      'name': 'Architecture & Tech Lead',
      'role_title': 'Thiết kế Hệ thống & Kiểm soát Chất lượng Code',
      'department': 'Engineering',
      'agent_type': 'specialist',
      'default_model_profile': 'code_intelligence',
      'risk_level': 3,
      'status': 'active',
      'enabled': true,
    },
    {
      'id': 'agent_fin_analyst',
      'key': 'cashflow_planner',
      'name': 'Finance & Budget Analyst',
      'role_title': 'Kiểm soát Ngân sách, Dòng tiền & Runway',
      'department': 'Finance',
      'agent_type': 'specialist',
      'default_model_profile': 'analytical',
      'risk_level': 2,
      'status': 'idle',
      'enabled': true,
    },
    {
      'id': 'agent_legal_officer',
      'key': 'compliance_analyst',
      'name': 'Legal & Compliance Officer',
      'role_title': 'Rà soát Hợp đồng & Tuân thủ Pháp lý',
      'department': 'Legal',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 1,
      'status': 'idle',
      'enabled': true,
    },
  ];

  List<Map<String, dynamic>> get _agents {
    final list = (widget.customAgents != null && widget.customAgents!.isNotEmpty)
        ? widget.customAgents!
        : _fallbackAgents;

    if (_selectedDept == 'All') return list;
    return list
        .where(
          (a) =>
              (a['department'] ?? '').toString().toLowerCase() ==
              _selectedDept.toLowerCase(),
        )
        .toList();
  }

  // Chỉ 1 card được mở khung chi tiết tại 1 thời điểm — mở card khác thì
  // đóng card đang mở, không tích luỹ nhiều card mở cùng lúc.
  void _toggleAgentExpanded(String id) {
    setState(() {
      if (_expandedAgentIds.contains(id)) {
        _expandedAgentIds.clear();
      } else {
        _expandedAgentIds
          ..clear()
          ..add(id);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.isCollapsed) {
      return _buildCollapsedRail();
    }
    return _buildExpandedSidebar();
  }

  Widget _buildCollapsedRail() {
    return Container(
      width: 68,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2), width: 1),
      ),
      child: Column(
        children: [
          const SizedBox(height: 12),
          IconButton(
            onPressed: widget.onToggleCollapse,
            icon: const Icon(Icons.chevron_right, color: AppTheme.primaryLight),
            tooltip: 'Mở rộng AI Workforce',
          ),
          Divider(color: AppTheme.primary.withValues(alpha: 0.13)),
          const SizedBox(height: 6),
          Builder(
            builder: (context) {
              final listWidget = ListView.builder(
                shrinkWrap: widget.shrinkWrap,
                physics: widget.shrinkWrap
                    ? const NeverScrollableScrollPhysics()
                    : null,
                itemCount: _agents.length,
                itemBuilder: (context, index) {
                  final agent = _agents[index];
                  final name = agent['name'] ?? 'Agent';
                  final role = agent['role_title'] ?? '';
                  final isActive = (agent['status'] ?? '') == 'active';

                  return Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: 8,
                      horizontal: 10,
                    ),
                    child: Tooltip(
                      message: '$name\n$role\n(Bấm để Chat giao việc)',
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF334155)),
                      ),
                      textStyle: const TextStyle(
                        color: Colors.white,
                        fontSize: 11.5,
                      ),
                      child: InkWell(
                        onTap: () => widget.onOpenChat(agent),
                        borderRadius: BorderRadius.circular(12),
                        child: Stack(
                          alignment: Alignment.bottomRight,
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: isActive
                                      ? [
                                          AppTheme.primary,
                                          AppTheme.primaryDark,
                                        ]
                                      : [
                                          const Color(0xFF334155),
                                          const Color(0xFF1E293B),
                                        ],
                                ),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: isActive
                                      ? AppTheme.primaryLight.withValues(alpha: 0.5)
                                      : const Color(0xFF475569),
                                ),
                              ),
                              child: Icon(
                                _getDeptIcon(agent['department'] ?? ''),
                                color: Colors.white,
                                size: 20,
                              ),
                            ),
                            Container(
                              width: 10,
                              height: 10,
                              margin: const EdgeInsets.only(
                                bottom: 2,
                                right: 2,
                              ),
                              decoration: BoxDecoration(
                                color: isActive
                                    ? const Color(0xFF10B981)
                                    : const Color(0xFF94A3B8),
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: const Color(0xFF0F172A),
                                  width: 1.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              );

              return widget.shrinkWrap
                  ? listWidget
                  : Expanded(child: listWidget);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildExpandedSidebar() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2), width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Header: AI Workforce + Nút đóng/mở dọc tất cả + Nút thu gọn cột
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppTheme.primary, AppTheme.primaryDark],
                  ),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.groups_outlined, color: Colors.white, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Flexible(
                          child: Text(
                            'AI WORKFORCE',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 0.5,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF10B981).withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${_agents.length} Online',
                            style: const TextStyle(
                              color: Color(0xFF34D399),
                              fontSize: 9.5,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Đóng/mở dọc từng Agent',
                      style: TextStyle(
                        color: Colors.white54,
                        fontSize: 10.5,
                      ),
                    ),
                  ],
                ),
              ),
              // Department filter — select gọn, đặt cạnh nút thu gọn cột
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _selectedDept,
                    dropdownColor: const Color(0xFF1E293B),
                    icon: const Icon(Icons.expand_more, color: AppTheme.primaryLight, size: 16),
                    style: const TextStyle(color: Colors.white, fontSize: 11.5),
                    items: _departments
                        .map(
                          (dept) => DropdownMenuItem(
                            value: dept,
                            child: Text(dept),
                          ),
                        )
                        .toList(),
                    onChanged: (val) {
                      if (val != null) setState(() => _selectedDept = val);
                    },
                  ),
                ),
              ),
              IconButton(
                onPressed: widget.onToggleCollapse,
                icon: const Icon(Icons.chevron_left, color: AppTheme.primaryLight),
                tooltip: 'Thu gọn cột AI Workforce',
              ),
            ],
          ),
          const SizedBox(height: 12),

          // 3. Agent list: Đóng/Mở theo chiều dọc (Vertical Expandable Cards)
          Builder(
            builder: (context) {
              final agentList = ListView.separated(
                shrinkWrap: widget.shrinkWrap,
                physics: widget.shrinkWrap
                    ? const NeverScrollableScrollPhysics()
                    : null,
                itemCount: _agents.length,
                separatorBuilder: (context, index) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final agent = _agents[index];
                  final id = agent['id']?.toString() ?? index.toString();
                  final isExpanded = _expandedAgentIds.contains(id);
                  return _buildVerticalAgentCard(agent, id, isExpanded);
                },
              );

              return widget.shrinkWrap ? agentList : Expanded(child: agentList);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildVerticalAgentCard(
    Map<String, dynamic> agent,
    String id,
    bool isExpanded,
  ) {
    final name = agent['name'] ?? 'Agent';
    final role = agent['role_title'] ?? '';
    final dept = agent['department'] ?? 'Operations';
    final status = agent['status'] ?? 'active';
    final isActive = status == 'active';
    final deptColor = _getDeptColor(dept);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: const Color(0xFF131D36),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isExpanded
              ? AppTheme.primary.withValues(alpha: 0.4)
              : (isActive ? AppTheme.primary.withValues(alpha: 0.13) : const Color(0xFF1E293B)),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Row Header: Bấm để đóng/mở theo chiều dọc
          InkWell(
            onTap: () => _toggleAgentExpanded(id),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [deptColor.withValues(alpha: 0.85), deptColor],
                      ),
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: Icon(_getDeptIcon(dept), color: Colors.white, size: 18),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (!isExpanded)
                          Text(
                            role,
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.5),
                              fontSize: 10.5,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      color: isActive ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Nút chat nhanh
                  IconButton(
                    onPressed: () => widget.onOpenChat(agent),
                    icon: const Icon(Icons.chat_bubble_outline, size: 15, color: AppTheme.primaryLight),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                    tooltip: 'Chat & Giao việc',
                  ),
                  // Mũi tên chỉ thị đóng/mở dọc
                  Icon(
                    isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    color: const Color(0xFF94A3B8),
                    size: 18,
                  ),
                ],
              ),
            ),
          ),

          // Nội dung mở rộng theo chiều dọc (khi mở khung card)
          if (isExpanded) ...[
            Divider(color: AppTheme.primary.withValues(alpha: 0.13), height: 1),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    role,
                    style: const TextStyle(
                      color: Color(0xFFCBD5E1),
                      fontSize: 11.5,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Tags
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: deptColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: deptColor.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          dept.toUpperCase(),
                          style: TextStyle(color: deptColor, fontSize: 9, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: const Color(0xFF334155)),
                        ),
                        child: Text(
                          'R${agent['risk_level'] ?? 2} RISK',
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 9, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // Action Buttons
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => widget.onOpenChat(agent),
                          icon: const Icon(Icons.chat_bubble_outline, size: 14, color: Colors.white),
                          label: const Text(
                            'Chat & Giao việc',
                            style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                            elevation: 0,
                          ),
                        ),
                      ),
                      if (widget.onOpenTestRun != null) ...[
                        const SizedBox(width: 6),
                        OutlinedButton(
                          onPressed: () => widget.onOpenTestRun!(agent),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppTheme.primaryLight,
                            side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.27)),
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.play_arrow_rounded, size: 14),
                              SizedBox(width: 2),
                              Text('Test', style: TextStyle(fontSize: 11)),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  IconData _getDeptIcon(String dept) {
    switch (dept.toLowerCase()) {
      case 'marketing':
        return Icons.campaign_rounded;
      case 'sales':
        return Icons.trending_up_rounded;
      case 'engineering':
        return Icons.code_rounded;
      case 'finance':
        return Icons.account_balance_wallet_rounded;
      case 'legal':
        return Icons.gavel_rounded;
      case 'operations':
      default:
        return Icons.smart_toy_outlined;
    }
  }

  Color _getDeptColor(String dept) {
    switch (dept.toLowerCase()) {
      case 'marketing':
        return const Color(0xFFEC4899);
      case 'sales':
        return const Color(0xFFF59E0B);
      case 'engineering':
        return const Color(0xFF3B82F6);
      case 'finance':
        return const Color(0xFF10B981);
      case 'legal':
        return const Color(0xFF8B5CF6);
      case 'operations':
      default:
        return AppTheme.primary;
    }
  }
}
