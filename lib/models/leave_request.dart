// models/leave_request.dart - نموذج طلب الإجازة كامل ومُصحح
import 'package:intl/intl.dart';

class LeaveRequest {
  final int id;
  final int employeeId;
  final int leaveTypeId;
  final String leaveTypeName;
  final DateTime dateFrom;
  final DateTime dateTo;
  final double numberOfDays;
  final String reason;
  final String state;
  final String stateText;
  final String stateIcon;
  final String stateColor;
  final DateTime createdDate;
  final String? approvedBy;
  final String? rejectedReason;

  // خصائص إضافية مطلوبة للصفحات
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
    required this.reason,
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

  factory LeaveRequest.fromJson(Map<String, dynamic> json) {
    return LeaveRequest(
      id: json['id'] ?? 0,
      employeeId: json['employee_id'] ?? 0,
      leaveTypeId: json['leave_type_id'] ?? 0,
      leaveTypeName: json['leave_type_name'] ?? '',
      dateFrom: DateTime.parse(json['date_from'] ?? DateTime.now().toIso8601String()),
      dateTo: DateTime.parse(json['date_to'] ?? DateTime.now().toIso8601String()),
      numberOfDays: (json['number_of_days'] ?? 0).toDouble(),
      reason: json['reason'] ?? '',
      state: json['state'] ?? 'draft',
      stateText: json['state_text'] ?? '',
      stateIcon: json['state_icon'] ?? '📝',
      stateColor: json['state_color'] ?? '#9E9E9E',
      createdDate: DateTime.parse(json['created_date'] ?? DateTime.now().toIso8601String()),
      approvedBy: json['approved_by'],
      rejectedReason: json['rejected_reason'],
      managerComment: json['manager_comment'],
      employeeName: json['employee_name'],
      approvalDate: json['approval_date'] != null ? DateTime.parse(json['approval_date']) : null,
      approverName: json['approver_name'],
    );
  }

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
      'approved_by': approvedBy,
      'rejected_reason': rejectedReason,
      'manager_comment': managerComment,
      'employee_name': employeeName,
      'approval_date': approvalDate?.toIso8601String(),
      'approver_name': approverName,
    };
  }

  // خصائص محسوبة للعرض
  String get formattedDateRange {
    final formatter = DateFormat('dd/MM/yyyy', 'ar');
    if (dateFrom.year == dateTo.year && dateFrom.month == dateTo.month && dateFrom.day == dateTo.day) {
      return formatter.format(dateFrom);
    }
    return '${formatter.format(dateFrom)} - ${formatter.format(dateTo)}';
  }

  String get formattedDuration {
    if (numberOfDays == 1) {
      return 'يوم واحد';
    } else if (numberOfDays == 2) {
      return 'يومان';
    } else if (numberOfDays <= 10) {
      return '${numberOfDays.toInt()} أيام';
    } else {
      return '${numberOfDays.toInt()} يوماً';
    }
  }

  String get formattedCreatedDate {
    final formatter = DateFormat('dd/MM/yyyy HH:mm', 'ar');
    return formatter.format(createdDate);
  }

  bool get canBeCancelled {
    return state == 'draft' || state == 'confirm';
  }

  bool get isPending {
    return state == 'draft' || state == 'confirm' || state == 'validate1';
  }

  bool get isApproved {
    return state == 'validate';
  }

  bool get isRejected {
    return state == 'refuse';
  }

  // خصائص إضافية للتوافق مع الصفحات
  DateTime get startDate => dateFrom;
  DateTime get endDate => dateTo;
  DateTime get requestDate => createdDate;

  bool get canCancel => canBeCancelled;
  bool get canEdit => state == 'draft';
}