import 'package:flutter/foundation.dart';

@immutable
class LeadModel {
  final String id;
  final String name;
  final String email;
  final String? phone;
  final String stage; // 'new', 'contacted', 'qualified', 'converted', 'disqualified'
  final int bantScore;
  final String? intent;
  final DateTime createdAt;

  const LeadModel({
    required this.id,
    required this.name,
    required this.email,
    this.phone,
    this.stage = 'new',
    this.bantScore = 0,
    this.intent,
    required this.createdAt,
  });

  factory LeadModel.fromJson(Map<String, dynamic> json) {
    return LeadModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      phone: json['phone']?.toString(),
      stage: json['stage']?.toString() ?? 'new',
      bantScore: (json['bant_score'] as num?)?.toInt() ?? (json['bantScore'] as num?)?.toInt() ?? (json['fitScore'] as num?)?.toInt() ?? 0,
      intent: json['intent']?.toString() ?? json['intentScore']?.toString(),
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? json['createdAt']?.toString() ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phone': phone,
      'stage': stage,
      'bant_score': bantScore,
      'intent': intent,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

@immutable
class OpportunityModel {
  final String id;
  final String name;
  final String accountId;
  final double amount;
  final String currency;
  final String stage; // 'prospecting', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'
  final String? winReason;
  final String? lostReason;
  final double probability;
  final DateTime createdAt;

  const OpportunityModel({
    required this.id,
    required this.name,
    required this.accountId,
    required this.amount,
    this.currency = 'VND',
    this.stage = 'prospecting',
    this.winReason,
    this.lostReason,
    this.probability = 0.1,
    required this.createdAt,
  });

  factory OpportunityModel.fromJson(Map<String, dynamic> json) {
    return OpportunityModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      accountId: json['account_id']?.toString() ?? json['accountId']?.toString() ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? (json['value'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency']?.toString() ?? 'VND',
      stage: json['stage']?.toString() ?? 'prospecting',
      winReason: json['win_reason']?.toString() ?? json['winReason']?.toString(),
      lostReason: json['lost_reason']?.toString() ?? json['lostReason']?.toString(),
      probability: (json['probability'] as num?)?.toDouble() ?? 0.1,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? json['createdAt']?.toString() ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'account_id': accountId,
      'amount': amount,
      'currency': currency,
      'stage': stage,
      'win_reason': winReason,
      'lost_reason': lostReason,
      'probability': probability,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

@immutable
class AccountModel {
  final String id;
  final String name;
  final String? domain;
  final String? industry;
  final String? size;
  final String? tier;

  const AccountModel({
    required this.id,
    required this.name,
    this.domain,
    this.industry,
    this.size,
    this.tier,
  });

  factory AccountModel.fromJson(Map<String, dynamic> json) {
    return AccountModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      domain: json['domain']?.toString(),
      industry: json['industry']?.toString(),
      size: json['size']?.toString(),
      tier: json['tier']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'domain': domain,
      'industry': industry,
      'size': size,
      'tier': tier,
    };
  }
}

@immutable
class CustomerModel {
  final String id;
  final String accountId;
  final String name;
  final double healthScore;
  final String lifecycleStatus; // 'onboarding', 'active', 'at_risk', 'churned'
  final double mrr;

  const CustomerModel({
    required this.id,
    required this.accountId,
    required this.name,
    this.healthScore = 100.0,
    this.lifecycleStatus = 'active',
    this.mrr = 0.0,
  });

  factory CustomerModel.fromJson(Map<String, dynamic> json) {
    return CustomerModel(
      id: json['id']?.toString() ?? '',
      accountId: json['account_id']?.toString() ?? json['accountId']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      healthScore: (json['health_score'] as num?)?.toDouble() ?? (json['healthScore'] as num?)?.toDouble() ?? 100.0,
      lifecycleStatus: json['lifecycle_status']?.toString() ?? json['lifecycleStatus']?.toString() ?? 'active',
      mrr: (json['mrr'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'account_id': accountId,
      'name': name,
      'health_score': healthScore,
      'lifecycle_status': lifecycleStatus,
      'mrr': mrr,
    };
  }
}

@immutable
class CampaignModel {
  final String id;
  final String name;
  final String status; // 'draft', 'active', 'paused', 'completed'
  final double budget;
  final double spend;
  final int impressions;
  final int conversions;
  final double roi;

  const CampaignModel({
    required this.id,
    required this.name,
    this.status = 'draft',
    this.budget = 0.0,
    this.spend = 0.0,
    this.impressions = 0,
    this.conversions = 0,
    this.roi = 0.0,
  });

  factory CampaignModel.fromJson(Map<String, dynamic> json) {
    return CampaignModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      status: json['status']?.toString() ?? 'draft',
      budget: (json['budget'] as num?)?.toDouble() ?? 0.0,
      spend: (json['spend'] as num?)?.toDouble() ?? 0.0,
      impressions: (json['impressions'] as num?)?.toInt() ?? 0,
      conversions: (json['conversions'] as num?)?.toInt() ?? 0,
      roi: (json['roi'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'status': status,
      'budget': budget,
      'spend': spend,
      'impressions': impressions,
      'conversions': conversions,
      'roi': roi,
    };
  }
}
