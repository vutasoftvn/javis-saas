import 'package:flutter/material.dart';
import 'approval_request_card.dart';
import 'artifact_viewer.dart';
import 'crm_lead_card.dart';
import 'pnl_statement_card.dart';
import 'runway_gauge_card.dart';
import 'terminal_output_card.dart';
import 'web_search_card.dart';

class ToolPresenterFactory {
  static Widget build(
    Map<String, dynamic>? payload, {
    VoidCallback? onApprove,
    VoidCallback? onReject,
  }) {
    if (payload == null || payload.isEmpty) {
      return const SizedBox.shrink();
    }

    final viewType = payload['view_type'] ?? '';

    switch (viewType) {
      case 'web_search_card':
        return WebSearchCardWidget(payload: payload);
      case 'crm_lead_summary_card':
      case 'lead_created_card':
        return CrmLeadCardWidget(payload: payload);
      case 'pnl_statement_card':
        return PnLStatementCardWidget(payload: payload);
      case 'runway_gauge_card':
        return RunwayGaugeCardWidget(payload: payload);
      case 'terminal_output_card':
        return TerminalOutputCardWidget(payload: payload);
      case 'approval_request_card':
        return ApprovalRequestCardWidget(
          payload: payload,
          onApprove: onApprove,
          onReject: onReject,
        );
      case 'file_preview_card':
      case 'file_created_card':
      case 'knowledge_doc_card':
        return ArtifactViewerWidget(payload: payload);
      default:
        return Container(
          padding: const EdgeInsets.all(8),
          margin: const EdgeInsets.symmetric(vertical: 4),
          decoration: BoxDecoration(
            color: const Color(0x10FFFFFF),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            payload['summary'] ?? payload['title'] ?? payload.toString(),
            style: const TextStyle(color: Colors.white70, fontSize: 12),
          ),
        );
    }
  }
}
