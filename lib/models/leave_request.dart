// lib/models/leave_request.dart - نموذج مُصحح ومبسط
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class LeaveRequest {
  final int id;
  final int employeeId;
  final int leaveTypeId;
  final String leaveTypeName;
  final DateTime dateFrom;
  final DateTime dateTo;
  final double numberOfDays;
  final String reason; // تم تغيير name إلى reason
  final String state;
  final String stateText;
  final String stateIcon;
  final String stateColor;
  final DateTime createdDate;
  final String? approvedBy;
  final String? rejectedReason;
  final String? managerComment;
  final String? employeeName;
  final DateTime? approvalDate;
  final String? approverName;

  LeaveRequest({
    required this.id,
    required this.employeeId,
    required this.leaveTypeId,
    required this.leaveTypeName,
    required this.dateFrom,
    required this.dateTo,
    required this.numberOfDays,
    required this.reason, // تم تصحيح هذا
    required this.state,
    required this.stateText,
    required this.stateIcon,
    required this.stateColor,
    required this.createdDate,
    this.approvedBy,
    this.rejectedReason,
    this.managerComment,
    this.employeeName,
    this.approvalDate,
    this.approverName,
  });

  // نسخ الطلب مع تحديث قيم معينة
  LeaveRequest copyWith({
    int? id,
    int? employeeId,
    int? leaveTypeId,
    String? leaveTypeName,
    DateTime? dateFrom,
    DateTime? dateTo,
    double? numberOfDays,
    String? reason,
    String? state,
    String? stateText,
    String? stateIcon,
    String? stateColor,
    DateTime? createdDate,
    String? approvedBy,
    String? rejectedReason,
    String? managerComment,
    String? employeeName,
    DateTime? approvalDate,
    String? approverName,
  }) {
    return LeaveRequest(
      id: id ?? this.id,
      employeeId: employeeId ?? this.employeeId,
      leaveTypeId: leaveTypeId ?? this.leaveTypeId,
      leaveTypeName: leaveTypeName ?? this.leaveTypeName,
      dateFrom: dateFrom ?? this.dateFrom,
      dateTo: dateTo ?? this.dateTo,
      numberOfDays: numberOfDays ?? this.numberOfDays,
      reason: reason ?? this.reason,
      state: state ?? this.state,
      stateText: stateText ?? this.stateText,
      stateIcon: stateIcon ?? this.stateIcon,
      stateColor: stateColor ?? this.stateColor,
      createdDate: createdDate ?? this.createdDate,
      approvedBy: approvedBy ?? this.approvedBy,
      rejectedReason: rejectedReason ?? this.rejectedReason,
      managerComment: managerComment ?? this.managerComment,
      employeeName: employeeName ?? this.employeeName,
      approvalDate: approvalDate ?? this.approvalDate,
      approverName: approverName ?? this.approverName,
    );
  }

  // تحويل إلى JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'employee_id': employeeId,
      'leave_type_id': leaveTypeId,
      'leave_type_name': leaveTypeName,
      'date_from': dateFrom.toIso8601String(),
      'date_to': dateTo.toIso8601String(),
      'number_of_days': numberOfDays,
      'reason': reason,
      'state': state,
      'state_text': stateText,
      'state_icon': stateIcon,
      'state_color': stateColor,
      'created_date': createdDate.toIso8601String(),
    };
  }

  // إنشاء من JSON
  factory LeaveRequest.fromJson(Map<String, dynamic> json) {
    return LeaveRequest(
      id: json['id'] ?? 0,
      employeeId: json['employee_id'] ?? 0,
      leaveTypeId: json['leave_type_id'] ?? 0,
      leaveTypeName: json['leave_type_name'] ?? 'غير محدد',
      dateFrom: DateTime.parse(json['date_from'] ?? DateTime.now().toIso8601String()),
      dateTo: DateTime.parse(json['date_to'] ?? DateTime.now().toIso8601String()),
      numberOfDays: (json['number_of_days'] ?? 1).toDouble(),
      reason: json['reason'] ?? json['name'] ?? '',
      state: json['state'] ?? 'draft',
      stateText: _getStateText(json['state'] ?? 'draft'),
      stateIcon: _getStateIcon(json['state'] ?? 'draft'),
      stateColor: _getStateColor(json['state'] ?? 'draft'),
      createdDate: DateTime.parse(json['created_date'] ?? DateTime.now().toIso8601String()),
    );
  }

  // خصائص محسوبة
  String get formattedDateRange {
    final formatter = DateFormat('dd/MM/yyyy', 'ar');
    if (dateFrom.day == dateTo.day && dateFrom.month == dateTo.month && dateFrom.year == dateTo.year) {
      return formatter.format(dateFrom);
    }
    return '${formatter.format(dateFrom)} - ${formatter.format(dateTo)}';
  }

  String get formattedDuration {
    final days = numberOfDays.toInt();
    if (days == 1) return 'يوم واحد';
    if (days == 2) return 'يومان';
    if (days <= 10) return '$days أيام';
    return '$days يوماً';
  }

  // خصائص للحالة
  bool get isPending => state == 'draft' || state == 'confirm';
  bool get isApproved => state == 'validate';
  bool get isRejected => state == 'refuse';
  bool get isCancelled => state == 'cancel';
  bool get canBeCancelled => state == 'draft' || state == 'confirm';
  bool get canEdit => state == 'draft';

  // للتوافق مع الكود القديم
  DateTime get startDate => dateFrom;
  DateTime get endDate => dateTo;
  DateTime get requestDate => createdDate;
  bool get canCancel => canBeCancelled;

  // فحص التداخل
  bool overlapsWith(LeaveRequest other) {
    return !(dateTo.isBefore(other.dateFrom) || dateFrom.isAfter(other.dateTo));
  }

  // دوال مساعدة للحالة
  static String _getStateText(String state) {
    switch (state) {
      case 'draft': return 'مسودة';
      case 'confirm': return 'قيد المراجعة';
      case 'validate1': return 'مراجعة أولى';
      case 'validate': return 'مقبولة';
      case 'refuse': return 'مرفوضة';
      case 'cancel': return 'ملغاة';
      default: return 'غير محدد';
    }
  }

  static String _getStateIcon(String state) {
    switch (state) {
      case 'draft': return '📝';
      case 'confirm': return '⏳';
      case 'validate1': return '👁️';
      case 'validate': return '✅';
      case 'refuse': return '❌';
      case 'cancel': return '🚫';
      default: return '❓';
    }
  }

  static String _getStateColor(String state) {
    switch (state) {
      case 'draft': return '#9E9E9E';
      case 'confirm': return '#FFA500';
      case 'validate1': return '#2196F3';
      case 'validate': return '#4CAF50';
      case 'refuse': return '#F44336';
      case 'cancel': return '#9E9E9E';
      default: return '#9E9E9E';
    }
  }

  @override
  String toString() {
    return 'LeaveRequest(id: $id, type: $leaveTypeName, dates: $formattedDateRange, state: $stateText)';
  }
}