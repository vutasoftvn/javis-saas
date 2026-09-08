import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/app_translations.dart';

enum TaskKanbanStatus {
  todo,
  inProgress,
  waitingApproval,
  blocked,
  done,
  cancelled;

  static TaskKanbanStatus fromString(String? val) {
    switch (val?.toString().toLowerCase()) {
      case 'in_progress':
      case 'inprogress':
        return TaskKanbanStatus.inProgress;
      case 'waiting_approval':
      case 'waitingapproval':
        return TaskKanbanStatus.waitingApproval;
      case 'blocked':
        return TaskKanbanStatus.blocked;
      case 'done':
      case 'completed':
        return TaskKanbanStatus.done;
      case 'cancelled':
        return TaskKanbanStatus.cancelled;
      case 'todo':
      default:
        return TaskKanbanStatus.todo;
    }
  }

  String get value {
    switch (this) {
      case TaskKanbanStatus.inProgress:
        return 'in_progress';
      case TaskKanbanStatus.waitingApproval:
        return 'waiting_approval';
      case TaskKanbanStatus.blocked:
        return 'blocked';
      case TaskKanbanStatus.done:
        return 'done';
      case TaskKanbanStatus.cancelled:
        return 'cancelled';
      case TaskKanbanStatus.todo:
        return 'todo';
    }
  }

  String get title {
    switch (this) {
      case TaskKanbanStatus.todo:
        return L10nKey.tasksStatusTodo.tr;
      case TaskKanbanStatus.inProgress:
        return L10nKey.tasksStatusInProgress.tr;
      case TaskKanbanStatus.waitingApproval:
        return L10nKey.tasksStatusWaitingApproval.tr;
      case TaskKanbanStatus.blocked:
        return L10nKey.tasksStatusBlocked.tr;
      case TaskKanbanStatus.done:
        return L10nKey.tasksStatusDone.tr;
      case TaskKanbanStatus.cancelled:
        return L10nKey.tasksStatusCancelled.tr;
    }
  }

  Color get color {
    switch (this) {
      case TaskKanbanStatus.todo:
        return const Color(0xFF38BDF8);
      case TaskKanbanStatus.inProgress:
        return const Color(0xFF00F0FF);
      case TaskKanbanStatus.waitingApproval:
        return const Color(0xFFF59E0B);
      case TaskKanbanStatus.blocked:
        return const Color(0xFFEF4444);
      case TaskKanbanStatus.done:
        return const Color(0xFF10B981);
      case TaskKanbanStatus.cancelled:
        return const Color(0xFF64748B);
    }
  }
}

class TaskKanbanModel {
  final String id;
  final String title;
  final String? description;
  final TaskKanbanStatus status;
  final String? assigneeName;
  final String? assigneeAvatar;
  final String? priority;
  final String? dueDate;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final Map<String, dynamic> metadata;

  const TaskKanbanModel({
    required this.id,
    required this.title,
    this.description,
    this.status = TaskKanbanStatus.todo,
    this.assigneeName,
    this.assigneeAvatar,
    this.priority,
    this.dueDate,
    this.createdAt,
    this.updatedAt,
    this.metadata = const {},
  });

  factory TaskKanbanModel.fromJson(Map<String, dynamic> json) {
    return TaskKanbanModel(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Untitled Task',
      description: json['description']?.toString(),
      status: TaskKanbanStatus.fromString(json['status']?.toString()),
      assigneeName: json['assignee_name']?.toString() ?? json['assignee']?.toString() ?? json['assigneeMemberId']?.toString(),
      assigneeAvatar: json['assignee_avatar']?.toString() ?? json['assigneeAvatar']?.toString(),
      priority: json['priority']?.toString(),
      dueDate: json['due_date']?.toString() ?? json['dueAt']?.toString(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : (json['createdAt'] != null ? DateTime.tryParse(json['createdAt'].toString()) : null),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString())
          : (json['updatedAt'] != null ? DateTime.tryParse(json['updatedAt'].toString()) : null),
      metadata: json['metadata'] is Map<String, dynamic> ? json['metadata'] as Map<String, dynamic> : {},
    );
  }

  TaskKanbanModel copyWith({
    String? id,
    String? title,
    String? description,
    TaskKanbanStatus? status,
    String? assigneeName,
    String? assigneeAvatar,
    String? priority,
    String? dueDate,
    DateTime? createdAt,
    DateTime? updatedAt,
    Map<String, dynamic>? metadata,
  }) {
    return TaskKanbanModel(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      status: status ?? this.status,
      assigneeName: assigneeName ?? this.assigneeName,
      assigneeAvatar: assigneeAvatar ?? this.assigneeAvatar,
      priority: priority ?? this.priority,
      dueDate: dueDate ?? this.dueDate,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      metadata: metadata ?? this.metadata,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'status': status.value,
      'assignee_name': assigneeName,
      'assignee_avatar': assigneeAvatar,
      'priority': priority,
      'due_date': dueDate,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'metadata': metadata,
    };
  }
}
