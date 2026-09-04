import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';

void main() {
  test('WorkforceRosterEntry.fromJson parses backend snake_case fields', () {
    final entry = WorkforceRosterEntry.fromJson({
      'id': 1,
      'key': 'cashflow_planner',
      'name': 'Cashflow Planner',
      'role_title': 'Đọc giao dịch, dự báo dòng tiền...',
      'department': 'Finance',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 2,
      'status': 'available',
      'enabled': true,
    });
    expect(entry.key, 'cashflow_planner');
    expect(entry.department, 'Finance');
    expect(entry.status, 'available');
    expect(entry.enabled, isTrue);
  });

  test('WorkforceWorkProduct.fromJson parses backend snake_case fields', () {
    final product = WorkforceWorkProduct.fromJson({
      'id': 'art_1',
      'title': 'Market brief Q1',
      'product_type': 'text/markdown',
      'status': 'READY',
      'author_agent_key': 'functional.market_research_specialist',
      'object_ref': 'object://brief-q1',
      'created_at': '2026-09-04T12:00:00.000Z',
    });
    expect(product.title, 'Market brief Q1');
    expect(product.objectRef, 'object://brief-q1');
  });

  test('WorkforceExceptionSummary.fromJson parses nested escalations list', () {
    final summary = WorkforceExceptionSummary.fromJson({
      'total': 1,
      'founder_gate_count': 0,
      'lead_notify_count': 1,
      'has_critical': false,
      'escalations': [
        {
          'id': 'run_1',
          'exception_type': 'run_failed',
          'tier': 'LEAD_NOTIFY',
          'status': 'OPEN',
          'agent_key': 'functional.cashflow_planner',
          'created_at': '2026-09-04T12:00:00.000Z',
        },
      ],
    });
    expect(summary.total, 1);
    expect(summary.escalations.single.id, 'run_1');
    expect(summary.escalations.single.tier, 'LEAD_NOTIFY');
  });

  test('WorkforceStageRoster.fromJson parses nested stage/roster/summary', () {
    final roster = WorkforceStageRoster.fromJson({
      'stage': {'stage_code': 'P2', 'task_count': 1},
      'roster': [
        {'task_id': 't1', 'title': 'Ship pricing page', 'priority': 'high', 'status': 'todo', 'project_id': 'proj_1'},
      ],
      'summary': {'total': 1, 'high_priority': 1, 'medium': 0, 'locked': 0},
    });
    expect(roster.stage.stageCode, 'P2');
    expect(roster.roster.single.taskId, 't1');
    expect(roster.summary.highPriority, 1);
  });

  test('WorkforceDashboardSummary.fromJson parses flat counts', () {
    final summary = WorkforceDashboardSummary.fromJson({
      'roster_total': 6,
      'roster_active': 1,
      'open_exceptions': 0,
      'pending_approvals': 0,
      'work_products_total': 0,
    });
    expect(summary.rosterTotal, 6);
    expect(summary.rosterActive, 1);
  });
}
