import 'package:flutter/material.dart';
import '../../../../core/responsive/adaptive_scaffold.dart';
import '../panes/center_workspace_pane.dart';
import '../panes/left_workforce_pane.dart';
import '../panes/right_inspector_pane.dart';

class HologramHubScreen extends StatefulWidget {
  const HologramHubScreen({super.key});

  @override
  State<HologramHubScreen> createState() => _HologramHubScreenState();
}

class _HologramHubScreenState extends State<HologramHubScreen> {
  String _selectedAgentId = "cofounder";
  String _selectedProjectId = "mID";
  final TextEditingController _inputController = TextEditingController();

  final List<Map<String, dynamic>> _messages = [
    {
      "sender": "assistant",
      "content": "Xin chào Founder! Tôi là Co-founder Orchestrator của COSA OS. Hãy cho tôi biết mục tiêu chiến lược của bạn hôm nay.",
      "timestamp": "09:00:00"
    }
  ];

  final List<Map<String, dynamic>> _trajectorySteps = [
    {
      "step_id": "step_01",
      "step_type": "request_received",
      "title": "Hệ thống sẵn sàng",
      "timestamp": "09:00:00",
      "badge": "LOW_RISK",
      "duration_ms": 10
    }
  ];

  Map<String, dynamic>? _activeStep;

  void _handleSendMessage([String? overrideText]) {
    final text = overrideText ?? _inputController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add({
        "sender": "user",
        "content": text,
        "timestamp": DateTime.now().toIso8601String()
      });
      _inputController.clear();

      // Thêm bước vào Trajectory
      _trajectorySteps.add({
        "step_id": "step_${_trajectorySteps.length + 1}",
        "step_type": "request_received",
        "title": "Chỉ thị: $text",
        "timestamp": DateTime.now().toIso8601String(),
        "badge": "USER"
      });

      // Phản hồi mô phỏng tương ứng
      _simulateAgentResponse(text);
    });
  }

  void _simulateAgentResponse(String userText) {
    final clean = userText.toLowerCase();

    if (clean.contains("chào")) {
      _messages.add({
        "sender": "assistant",
        "content": "Chào bạn! Tôi có thể hỗ trợ gì cho dự án $_selectedProjectId hôm nay?",
        "timestamp": DateTime.now().toIso8601String()
      });
      _trajectorySteps.add({
        "step_id": "step_${_trajectorySteps.length + 1}",
        "step_type": "intent_classified",
        "title": "Ý định: conversation.greeting (Zero Context Load)",
        "timestamp": DateTime.now().toIso8601String(),
        "badge": "LOW_RISK"
      });
    } else if (clean.contains("thị trường") || clean.contains("đối thủ")) {
      _messages.add({
        "sender": "assistant",
        "content": "Đã thực hiện phân tích thị trường ngách và đối thủ cạnh tranh cho dự án $_selectedProjectId:",
        "presenter_payload": {
          "view_type": "web_search_card",
          "title": "Kết quả nghiên cứu thị trường EdTech Vietnam 2026",
          "items": [
            {"title": "Báo cáo Thị trường EdTech 2026", "snippet": "Thị trường đạt quy mô 1.5 tỷ USD với tốc độ CAGR 18%."},
            {"title": "Phân tích 3 Đối thủ Đầu ngành", "snippet": "Topica, ELSA, Manabie đang chiếm lĩnh 60% thị phần."}
          ]
        },
        "timestamp": DateTime.now().toIso8601String()
      });
      _trajectorySteps.add({
        "step_id": "step_${_trajectorySteps.length + 1}",
        "step_type": "tool_executed",
        "title": "Thực thi công cụ: web.search",
        "timestamp": DateTime.now().toIso8601String(),
        "badge": "LOW_RISK",
        "duration_ms": 820
      });
    } else if (clean.contains("p&l") || clean.contains("tài chính")) {
      _messages.add({
        "sender": "assistant",
        "content": "Báo cáo tài chính P&L theo chuẩn Thông tư 58:",
        "presenter_payload": {
          "view_type": "pnl_statement_card",
          "title": "Báo cáo Kết quả Kinh doanh Q1-2026",
          "metrics": [
            {"label": "Doanh thu", "value": "250,000,000 đ"},
            {"label": "Giá vốn hàng bán (COGS)", "value": "50,000,000 đ"},
            {"label": "Lợi nhuận gộp", "value": "200,000,000 đ"},
            {"label": "Chi phí vận hành", "value": "120,000,000 đ"},
            {"label": "Lợi nhuận ròng (Net Profit)", "value": "80,000,000 đ"}
          ]
        },
        "timestamp": DateTime.now().toIso8601String()
      });
    } else if (clean.contains("deploy")) {
      _messages.add({
        "sender": "assistant",
        "content": "Phát hiện hành động có rủi ro cao. Bắt buộc có sự xác nhận của Founder:",
        "presenter_payload": {
          "view_type": "approval_request_card",
          "title": "Yêu cầu Phê duyệt Triển khai Staging",
          "tool_id": "deployment.deploy_staging",
          "risk_level": "HIGH",
          "input_params": {"branch": "main", "target": "staging.cosa.ai"}
        },
        "timestamp": DateTime.now().toIso8601String()
      });
      _trajectorySteps.add({
        "step_id": "step_${_trajectorySteps.length + 1}",
        "step_type": "approval_pending",
        "title": "Chờ Founder phê duyệt Deploy",
        "timestamp": DateTime.now().toIso8601String(),
        "badge": "HIGH_RISK"
      });
    }
  }

  void _handleApprove() {
    setState(() {
      _messages.add({
        "sender": "assistant",
        "content": "Đã phê duyệt! Tiến hành triển khai Staging thành công.",
        "presenter_payload": {
          "view_type": "terminal_output_card",
          "title": "Deployment Pipeline Output",
          "exit_code": 0,
          "output": "Building Docker container...\nUploading to Hostinger VPS...\nHealthcheck: 200 OK"
        }
      });
      _trajectorySteps.add({
        "step_id": "step_${_trajectorySteps.length + 1}",
        "step_type": "tool_executed",
        "title": "Triển khai Staging: Thành công",
        "timestamp": DateTime.now().toIso8601String(),
        "badge": "APPROVED",
        "duration_ms": 3400
      });
    });
  }

  void _handleReject() {
    setState(() {
      _messages.add({
        "sender": "assistant",
        "content": "Hành động đã bị Founder từ chối.",
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return AdaptiveScaffold(
      leftPane: LeftWorkforcePane(
        selectedAgentId: _selectedAgentId,
        selectedProjectId: _selectedProjectId,
        onAgentSelected: (aid) => setState(() => _selectedAgentId = aid),
        onProjectSelected: (pid) => setState(() => _selectedProjectId = pid),
      ),
      centerPane: CenterWorkspacePane(
        activeAgentId: _selectedAgentId,
        messages: _messages,
        inputController: _inputController,
        onSendMessage: _handleSendMessage,
        onQuickChipSelected: (chip) => _handleSendMessage(chip),
        onApproveAction: _handleApprove,
        onRejectAction: _handleReject,
      ),
      rightPane: RightInspectorPane(
        trajectorySteps: _trajectorySteps,
        activeStep: _activeStep,
        onStepSelected: (st) => setState(() => _activeStep = st),
      ),
    );
  }
}
