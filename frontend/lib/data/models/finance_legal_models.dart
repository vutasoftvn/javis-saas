import 'package:flutter/foundation.dart';

@immutable
class AccountingProfileModel {
  final String id;
  final String mode; // 'standard', 'simplified', 'micro'
  final bool active;
  final DateTime? createdAt;

  const AccountingProfileModel({
    required this.id,
    required this.mode,
    this.active = true,
    this.createdAt,
  });

  factory AccountingProfileModel.fromJson(Map<String, dynamic> json) {
    return AccountingProfileModel(
      id: json['id']?.toString() ?? '',
      mode: json['mode']?.toString() ?? 'standard',
      active: json['active'] == true || json['is_active'] == true,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mode': mode,
      'active': active,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  AccountingProfileModel copyWith({
    String? id,
    String? mode,
    bool? active,
    DateTime? createdAt,
  }) {
    return AccountingProfileModel(
      id: id ?? this.id,
      mode: mode ?? this.mode,
      active: active ?? this.active,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}

@immutable
class AccountingPeriodModel {
  final String id;
  final DateTime startDate;
  final DateTime endDate;
  final String status; // 'open', 'closed', 'locked'
  final bool isLocked;

  const AccountingPeriodModel({
    required this.id,
    required this.startDate,
    required this.endDate,
    this.status = 'open',
    this.isLocked = false,
  });

  factory AccountingPeriodModel.fromJson(Map<String, dynamic> json) {
    return AccountingPeriodModel(
      id: json['id']?.toString() ?? '',
      startDate: DateTime.tryParse(json['start_date']?.toString() ?? '') ?? DateTime.now(),
      endDate: DateTime.tryParse(json['end_date']?.toString() ?? '') ?? DateTime.now(),
      status: json['status']?.toString() ?? 'open',
      isLocked: json['is_locked'] == true || json['status'] == 'locked',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'start_date': startDate.toIso8601String(),
      'end_date': endDate.toIso8601String(),
      'status': status,
      'is_locked': isLocked,
    };
  }
}

@immutable
class FinancialTransactionModel {
  final String id;
  final String type; // 'income', 'expense', 'transfer'
  final double amount;
  final String currency;
  final String category;
  final String description;
  final DateTime transactionDate;
  final String? evidenceUrl;
  final String? accountCode;

  const FinancialTransactionModel({
    required this.id,
    required this.type,
    required this.amount,
    this.currency = 'VND',
    required this.category,
    this.description = '',
    required this.transactionDate,
    this.evidenceUrl,
    this.accountCode,
  });

  factory FinancialTransactionModel.fromJson(Map<String, dynamic> json) {
    return FinancialTransactionModel(
      id: json['id']?.toString() ?? '',
      type: json['type']?.toString() ?? 'expense',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency']?.toString() ?? 'VND',
      category: json['category']?.toString() ?? 'general',
      description: json['description']?.toString() ?? '',
      transactionDate: DateTime.tryParse(json['transaction_date']?.toString() ?? json['date']?.toString() ?? '') ?? DateTime.now(),
      evidenceUrl: json['evidence_url']?.toString(),
      accountCode: json['account_code']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'amount': amount,
      'currency': currency,
      'category': category,
      'description': description,
      'transaction_date': transactionDate.toIso8601String(),
      'evidence_url': evidenceUrl,
      'account_code': accountCode,
    };
  }
}

@immutable
class FinanceSnapshotModel {
  final String periodId;
  final double totalIncome;
  final double totalExpense;
  final double netCashflow;
  final double runwayMonths;
  final DateTime generatedAt;

  const FinanceSnapshotModel({
    required this.periodId,
    required this.totalIncome,
    required this.totalExpense,
    required this.netCashflow,
    this.runwayMonths = 0.0,
    required this.generatedAt,
  });

  factory FinanceSnapshotModel.fromJson(Map<String, dynamic> json) {
    return FinanceSnapshotModel(
      periodId: json['period_id']?.toString() ?? '',
      totalIncome: (json['total_income'] as num?)?.toDouble() ?? 0.0,
      totalExpense: (json['total_expense'] as num?)?.toDouble() ?? 0.0,
      netCashflow: (json['net_cashflow'] as num?)?.toDouble() ?? 0.0,
      runwayMonths: (json['runway_months'] as num?)?.toDouble() ?? 0.0,
      generatedAt: DateTime.tryParse(json['generated_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'period_id': periodId,
      'total_income': totalIncome,
      'total_expense': totalExpense,
      'net_cashflow': netCashflow,
      'runway_months': runwayMonths,
      'generated_at': generatedAt.toIso8601String(),
    };
  }
}

@immutable
class LegalObligationModel {
  final String id;
  final String title;
  final String category; // 'tax', 'corporate', 'labor', 'compliance'
  final DateTime dueDate;
  final String status; // 'pending', 'in_progress', 'completed', 'overdue'
  final String? penaltyRisk;

  const LegalObligationModel({
    required this.id,
    required this.title,
    required this.category,
    required this.dueDate,
    this.status = 'pending',
    this.penaltyRisk,
  });

  factory LegalObligationModel.fromJson(Map<String, dynamic> json) {
    return LegalObligationModel(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      category: json['category']?.toString() ?? 'compliance',
      dueDate: DateTime.tryParse(json['due_date']?.toString() ?? '') ?? DateTime.now(),
      status: json['status']?.toString() ?? 'pending',
      penaltyRisk: json['penalty_risk']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'category': category,
      'due_date': dueDate.toIso8601String(),
      'status': status,
      'penalty_risk': penaltyRisk,
    };
  }
}

@immutable
class LegalChecklistItemModel {
  final String id;
  final String obligationId;
  final String content;
  final bool isCompleted;
  final String? verifiedBy;

  const LegalChecklistItemModel({
    required this.id,
    required this.obligationId,
    required this.content,
    this.isCompleted = false,
    this.verifiedBy,
  });

  factory LegalChecklistItemModel.fromJson(Map<String, dynamic> json) {
    return LegalChecklistItemModel(
      id: json['id']?.toString() ?? '',
      obligationId: json['obligation_id']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      isCompleted: json['is_completed'] == true,
      verifiedBy: json['verified_by']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'obligation_id': obligationId,
      'content': content,
      'is_completed': isCompleted,
      'verified_by': verifiedBy,
    };
  }
}
