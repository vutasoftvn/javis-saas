import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class AiTeamHelpers {
  static Color getRiskColor(String risk) {
    switch (risk.toUpperCase()) {
      case 'CRITICAL':
        return AppTheme.error;
      case 'HIGH':
        return const Color(0xFFF97316);
      case 'MEDIUM':
        return AppTheme.warning;
      default:
        return AppTheme.success;
    }
  }

  static String translateDepartment(String? dept) {
    switch (dept?.toLowerCase()) {
      case 'executive':
      case 'executive office':
        return 'Điều hành Chiến lược';
      case 'finance':
        return 'Tài chính & Kế toán';
      case 'growth':
      case 'marketing':
        return 'Marketing & Tăng trưởng';
      case 'sales':
        return 'Kinh doanh & Bán hàng';
      case 'tech':
      case 'engineering':
      case 'product':
        return 'Kỹ thuật & Công nghệ';
      case 'operations':
      case 'legal':
      case 'legal & compliance':
        return 'Vận hành & Pháp lý';
      case 'human resources':
      case 'hr':
        return 'Nhân sự & Văn hóa';
      default:
        return dept ?? 'Chung';
    }
  }

  static String translateModelProfile(String profile) {
    switch (profile.toLowerCase()) {
      case 'reasoning':
        return 'Tư duy sâu';
      case 'fast':
        return 'Tốc độ cao';
      case 'coding':
        return 'Lập trình';
      default:
        return profile;
    }
  }

  static IconData getDepartmentIcon(String? dept) {
    switch (dept?.toLowerCase()) {
      case 'executive':
      case 'executive office':
        return Icons.military_tech_rounded;
      case 'finance':
        return Icons.account_balance_wallet_rounded;
      case 'growth':
      case 'marketing':
        return Icons.campaign_rounded;
      case 'sales':
        return Icons.point_of_sale_rounded;
      case 'tech':
      case 'engineering':
      case 'product':
        return Icons.code_rounded;
      case 'operations':
      case 'legal':
      case 'legal & compliance':
        return Icons.gavel_rounded;
      case 'human resources':
      case 'hr':
        return Icons.people_alt_rounded;
      default:
        return Icons.smart_toy_rounded;
    }
  }

  static String getAgentPromptKey(Map<String, dynamic> agent) {
    if (agent['system_prompt_key'] != null &&
        agent['system_prompt_key'].toString().isNotEmpty) {
      return agent['system_prompt_key'].toString();
    }
    final key = (agent['key'] ?? '').toString().toLowerCase();
    switch (key) {
      case 'founder_copilot':
      case 'founder':
        return 'founder.system';
      case 'general':
      case 'general_assistant':
        return 'general.system';
      case 'cfo_agent':
      case 'finance':
        return 'finance.system';
      case 'cmo_agent':
      case 'marketing':
        return 'marketing.system';
      case 'sales_agent':
      case 'sales':
        return 'sales.system';
      case 'tech_lead_agent':
      case 'cto_agent':
        return 'tech_lead.system';
      case 'developer':
        return 'developer.system';
      case 'devops_agent':
        return 'devops.system';
      case 'legal_agent':
        return 'legal.system';
      case 'hr_agent':
        return 'hr.system';
      case 'product_agent':
        return 'product.system';
      case 'data_analyst_agent':
        return 'data_analyst.system';
      default:
        return '$key.system';
    }
  }

  static List<String> getAgentToolsList(Map<String, dynamic> agent) {
    if (agent['tools'] is List && (agent['tools'] as List).isNotEmpty) {
      return (agent['tools'] as List).map((e) => e.toString()).toList();
    }
    final key = (agent['key'] ?? '').toString().toLowerCase();
    switch (key) {
      case 'founder_copilot':
      case 'founder':
        return [
          'strategy.read_canvas',
          'okr.read_overview',
          'finance.read_summary',
          'tasks.create',
          'runtime.handoff.create',
          'policy.funding.search',
        ];
      case 'cfo_agent':
      case 'finance':
        return [
          'finance.read_summary',
          'finance.read_details',
          'finance.post_entry',
          'cost_ledger.audit',
          'agent_budgets.check_limit',
        ];
      case 'cmo_agent':
      case 'marketing':
        return [
          'marketing.campaign.create',
          'marketing.content.generate',
          'marketing.social.publish',
          'form.analyze',
        ];
      case 'sales_agent':
      case 'sales':
        return [
          'crm.search',
          'crm.update',
          'email.draft',
          'email.send',
          'sales.forecast',
        ];
      case 'tech_lead_agent':
      case 'cto_agent':
        return [
          'developer.build_spec.create',
          'developer.claude_code',
          'sandbox.execute',
          'mcp.github_search',
        ];
      case 'developer':
        return [
          'developer.claude_code',
          'sandbox.execute',
          'code_review',
          'unit_test.run',
        ];
      case 'devops_agent':
        return [
          'infra.monitor',
          'ci_cd.trigger',
          'server.diagnostics',
          'incident.resolve',
        ];
      case 'legal_agent':
        return [
          'contracts.review',
          'compliance.check',
          'policy.funding.search',
        ];
      case 'hr_agent':
        return [
          'org_structure.read',
          'kpi.track',
          'onboarding.guide',
        ];
      case 'product_agent':
        return [
          'prd.spec.create',
          'roadmap.update',
          'feedback.analyze',
        ];
      case 'data_analyst_agent':
        return [
          'scoreboard.read',
          'metrics.aggregate',
          'reports.generate',
        ];
      default:
        return ['knowledge.search', 'system.help', 'docs.read'];
    }
  }

  static String getAgentDefaultPromptContent(
      String promptKey, String name, String role) {
    return '''# VAI TRÒ & NHIỆM VỤ: $name ($role)
Bạn là thành viên trong Đội ngũ 12 Nhân sự AI (COSA Workforce Control Plane) phục vụ trực tiếp cho Founder.

## NGUYÊN TẮC HOẠT ĐỘNG:
1. Luôn bám sát mục tiêu 12-Week Year và dữ liệu thực tế của doanh nghiệp.
2. Tự động kiểm tra rủi ro (Risk Level). Nếu tác vụ vượt quá thẩm quyền hoặc có rủi ro cao, phải tạo Phiếu Phê duyệt (Approval Request) cho Founder.
3. Bàn giao kết quả rõ ràng, có cấu trúc dưới dạng Work Product bàn giao.

## CÔNG CỤ ĐƯỢC PHÉP SỬ DỤNG:
- Tuân thủ nghiêm ngặt danh sách Tool/Skill đã được cấu hình trong Tool Gateway.
''';
  }
}
