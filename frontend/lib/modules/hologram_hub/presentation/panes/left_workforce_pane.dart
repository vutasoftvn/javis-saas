import 'package:flutter/material.dart';

class LeftWorkforcePane extends StatelessWidget {
  final String selectedAgentId;
  final String selectedProjectId;
  final Function(String agentId)? onAgentSelected;
  final Function(String projectId)? onProjectSelected;

  const LeftWorkforcePane({
    super.key,
    this.selectedAgentId = "cofounder",
    this.selectedProjectId = "mID",
    this.onAgentSelected,
    this.onProjectSelected,
  });

  static const List<Map<String, String>> workforceAgents = [
    {"id": "cofounder", "name": "Co-founder", "role": "Orchestrator", "icon": "psychology"},
    {"id": "marketing", "name": "CMO", "role": "Marketing", "icon": "campaign"},
    {"id": "sales", "name": "Head of Sales", "role": "Sales Pipeline", "icon": "point_of_sale"},
    {"id": "finance", "name": "CFO", "role": "Finance & TT58", "icon": "account_balance"},
    {"id": "legal", "name": "General Counsel", "role": "Legal & Compliance", "icon": "gavel"},
    {"id": "research", "name": "Head of Research", "role": "Market Intelligence", "icon": "biotech"},
    {"id": "product", "name": "CPO", "role": "Product & PMF", "icon": "inventory_2"},
    {"id": "tech", "name": "CTO", "role": "Clean Architecture", "icon": "terminal"},
    {"id": "operations", "name": "COO", "role": "OKR & 12WY", "icon": "settings_suggest"},
    {"id": "hr", "name": "Head of HR", "role": "Talent & Culture", "icon": "groups"},
    {"id": "growth", "name": "Head of Growth", "role": "Acquisition AARRR", "icon": "trending_up"},
    {"id": "customer_success", "name": "Head of CS", "role": "NPS & Churn", "icon": "support_agent"},
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0D121D),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Project Selector Header
          Container(
            padding: const EdgeInsets.all(14),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0x1FFFFFFF))),
            ),
            child: Row(
              children: [
                const Icon(Icons.rocket_launch, color: Color(0xFF00F0FF), size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("DỰ ÁN MỤC TIÊU", style: TextStyle(color: Colors.white38, fontSize: 10, fontWeight: FontWeight.bold)),
                      Text(selectedProjectId, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.swap_horiz, color: Colors.white54, size: 18),
                  tooltip: "Đổi dự án",
                  onPressed: () => onProjectSelected?.call(selectedProjectId == "mID" ? "COSA" : "mID"),
                )
              ],
            ),
          ),

          // Workforce Section Header
          const Padding(
            padding: EdgeInsets.fromLTRB(14, 12, 14, 6),
            child: Text(
              "WORKFORCE ROSTER (12 AGENTS)",
              style: TextStyle(color: Color(0xFF00F0FF), fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
            ),
          ),

          // 12 Agents List
          Expanded(
            child: ListView.builder(
              itemCount: workforceAgents.length,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              itemBuilder: (context, index) {
                final agent = workforceAgents[index];
                final isSelected = agent["id"] == selectedAgentId;

                return InkWell(
                  onTap: () => onAgentSelected?.call(agent["id"]!),
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    margin: const EdgeInsets.symmetric(vertical: 2),
                    decoration: BoxDecoration(
                      color: isSelected ? const Color(0x2500F0FF) : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                      border: isSelected ? Border.all(color: const Color(0x6000F0FF)) : null,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          _getIcon(agent["icon"]!),
                          color: isSelected ? const Color(0xFF00F0FF) : Colors.white60,
                          size: 16,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                agent["name"]!,
                                style: TextStyle(
                                  color: isSelected ? const Color(0xFF00F0FF) : Colors.white,
                                  fontSize: 13,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                ),
                              ),
                              Text(
                                agent["role"]!,
                                style: const TextStyle(color: Colors.white38, fontSize: 10),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            color: isSelected ? const Color(0xFF00FF66) : const Color(0x40FFFFFF),
                            shape: BoxShape.circle,
                          ),
                        )
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  IconData _getIcon(String iconName) {
    switch (iconName) {
      case "psychology": return Icons.psychology;
      case "campaign": return Icons.campaign_outlined;
      case "point_of_sale": return Icons.point_of_sale;
      case "account_balance": return Icons.account_balance;
      case "gavel": return Icons.gavel;
      case "biotech": return Icons.biotech;
      case "inventory_2": return Icons.inventory_2_outlined;
      case "terminal": return Icons.terminal;
      case "settings_suggest": return Icons.settings_suggest;
      case "groups": return Icons.groups;
      case "trending_up": return Icons.trending_up;
      case "support_agent": return Icons.support_agent;
      default: return Icons.smart_toy_outlined;
    }
  }
}
