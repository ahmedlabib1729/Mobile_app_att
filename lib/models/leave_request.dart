// lib/models/leave_request.dart - نموذج طلب الإجازة كامل ومُصحح
import 'dart:ui';

import 'package:intl/intl.dart';

// تعداد حالات طلب الإجازة
enum LeaveRequestState {
  draft,
  confirm,
  validate1,
  validate,
  refuse,
  cancel,
}

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
    try {
      // معالجة التواريخ بطريقة آمنة
      DateTime parseDate(dynamic dateValue) {
        if (dateValue == null || dateValue == false) {
          return DateTime.now();
        }

        if (dateValue is String) {
          try {
            // إذا كان التاريخ بتنسيق Odoo (YYYY-MM-DD HH:MM:SS)
            if (dateValue.contains(' ')) {
              return DateTime.parse(dateValue);
            } else {
              // إذا كان التاريخ بدون وقت
              return DateTime.parse('$dateValue 00:00:00');
            }
          } catch (e) {
            print('خطأ في تحويل التاريخ: $dateValue, الخطأ: $e');
            return DateTime.now();
          }
        }

        return DateTime.now();
      }

      // معالجة الحقول المركبة من Odoo
      String extractName(dynamic field, String fallback) {
        if (field == null || field == false) return fallback;
        if (field is List && field.length > 1) return field[1].toString();
        if (field is String) return field;
        return fallback;
      }

      int extractId(dynamic field, int fallback) {
        if (field == null || field == false) return fallback;
        if (field is List && field.isNotEmpty) return field[0] as int;
        if (field is int) return field;
        return fallback;
      }

      // تحديد حالة الطلب
      final stateValue = json['state']?.toString() ?? 'draft';

      return LeaveRequest(
        id: json['id'] ?? 0,
        employeeId: extractId(json['employee_id'], 0),
        leaveTypeId: extractId(json['holiday_status_id'] ?? json['leave_type_id'], 0),
        leaveTypeName: extractName(json['holiday_status_id'] ?? json['leave_type_name'], 'غير محدد'),
        dateFrom: parseDate(json['date_from'] ?? json['request_date_from']),
        dateTo: parseDate(json['date_to'] ?? json['request_date_to']),
        numberOfDays: (json['number_of_days'] ?? json['number_of_days_display'] ?? 1).toDouble(),
        reason: json['name'] ?? json['reason'] ?? '',
        state: stateValue,
        stateText: _getStateText(stateValue),
        stateIcon: _getStateIcon(stateValue),
        stateColor: _getStateColor(stateValue),
        createdDate: parseDate(json['create_date'] ?? json['created_date']),
        approvedBy: json['approved_by'],
        rejectedReason: json['rejected_reason'],
        managerComment: json['manager_comment'] ?? json['notes'],
        employeeName: extractName(json['employee_id'] ?? json['employee_name'], ''),
        approvalDate: json['approval_date'] != null ? parseDate(json['approval_date']) : null,
        approverName: json['approver_name'],
      );
    } catch (e) {
      print('خطأ في تحويل LeaveRequest من JSON: $e');
      print('البيانات المستلمة: $json');

      // إرجاع طلب افتراضي في حالة الخطأ
      return LeaveRequest(
        id: json['id'] ?? 0,
        employeeId: 0,
        leaveTypeId: 0,
        leaveTypeName: 'غير محدد',
        dateFrom: DateTime.now(),
        dateTo: DateTime.now(),
        numberOfDays: 1,
        reason: json['name'] ?? '',
        state: 'draft',
        stateText: 'مسودة',
        stateIcon: '📝',
        stateColor: '#9E9E9E',
        createdDate: DateTime.now(),
      );
    }
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

  // خصائص محسوبة للعرض
  String get formattedDateRange {
    final formatter = DateFormat('dd/MM/yyyy', 'ar');

    // إذا كان نفس اليوم
    if (dateFrom.year == dateTo.year &&
        dateFrom.month == dateTo.month &&
        dateFrom.day == dateTo.day) {
      return formatter.format(dateFrom);
    }

    return '${formatter.format(dateFrom)} - ${formatter.format(dateTo)}';
  }

  String get formattedDuration {
    final days = numberOfDays.toInt();

    if (days == 1) {
      return 'يوم واحد';
    } else if (days == 2) {
      return 'يومان';
    } else if (days <= 10) {
      return '$days أيام';
    } else {
      return '$days يوماً';
    }
  }

  String get formattedCreatedDate {
    final formatter = DateFormat('dd/MM/yyyy HH:mm', 'ar');
    return formatter.format(createdDate);
  }

  String get formattedApprovalDate {
    if (approvalDate == null) return '';
    final formatter = DateFormat('dd/MM/yyyy HH:mm', 'ar');
    return formatter.format(approvalDate!);
  }

  // الخصائص المنطقية
  bool get canBeCancelled {
    return state == 'draft' || state == 'confirm';
  }

  bool get canEdit {
    return state == 'draft';
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

  bool get isCancelled {
    return state == 'cancel';
  }

  // خصائص إضافية للتوافق مع الصفحات
  DateTime get startDate => dateFrom;
  DateTime get endDate => dateTo;
  DateTime get requestDate => createdDate;
  bool get canCancel => canBeCancelled;

  // تحديد نوع الطلب حسب الحالة
  LeaveRequestState get requestState {
    switch (state) {
      case 'draft':
        return LeaveRequestState.draft;
      case 'confirm':
        return LeaveRequestState.confirm;
      case 'validate1':
        return LeaveRequestState.validate1;
      case 'validate':
        return LeaveRequestState.validate;
      case 'refuse':
        return LeaveRequestState.refuse;
      case 'cancel':
        return LeaveRequestState.cancel;
      default:
        return LeaveRequestState.draft;
    }
  }

  // فحص ما إذا كان الطلب في المستقبل
  bool get isFutureRequest {
    return dateFrom.isAfter(DateTime.now());
  }

  // فحص ما إذا كان الطلب في الماضي
  bool get isPastRequest {
    return dateTo.isBefore(DateTime.now());
  }

  // فحص ما إذا كان الطلب نشط حالياً
  bool get isActiveNow {
    final now = DateTime.now();
    return now.isAfter(dateFrom) && now.isBefore(dateTo) && isApproved;
  }

  // حساب المدة المتبقية للطلب
  Duration? get timeUntilStart {
    if (isFutureRequest) {
      return dateFrom.difference(DateTime.now());
    }
    return null;
  }

  // الحصول على ملخص للطلب
  String get summary {
    return '$leaveTypeName - ${formattedDateRange} ($formattedDuration)';
  }

  // تحديد أولوية الطلب
  int get priority {
    switch (state) {
      case 'draft':
        return 1;
      case 'confirm':
        return 2;
      case 'validate1':
        return 3;
      case 'validate':
        return 4;
      case 'refuse':
        return 5;
      case 'cancel':
        return 6;
      default:
        return 0;
    }
  }

  // الحصول على وصف تفصيلي للحالة
  String get detailedStatusDescription {
    switch (state) {
      case 'draft':
        return 'الطلب في مرحلة المسودة ولم يتم إرساله بعد';
      case 'confirm':
        return 'تم إرسال الطلب وهو في انتظار مراجعة المدير';
      case 'validate1':
        return 'الطلب قيد المراجعة من قبل المدير المباشر';
      case 'validate':
        return 'تم قبول الطلب وموافقة عليه';
      case 'refuse':
        return 'تم رفض الطلب من قبل الإدارة';
      case 'cancel':
        return 'تم إلغاء الطلب';
      default:
        return 'حالة غير معروفة';
    }
  }

  // الحصول على لون الحالة كـ Color object (للاستخدام في Flutter)
  Color get statusColorObject {
    return Color(int.parse('0xFF${stateColor.substring(1)}'));
  }

  // دوال مساعدة للحصول على نص الحالة والأيقونة واللون
  static String _getStateText(String state) {
    switch (state) {
      case 'draft':
        return 'مسودة';
      case 'confirm':
        return 'قيد المراجعة';
      case 'validate1':
        return 'مراجعة المدير';
      case 'validate':
        return 'مقبولة';
      case 'refuse':
        return 'مرفوضة';
      case 'cancel':
        return 'ملغاة';
      default:
        return 'غير محدد';
    }
  }

  static String _getStateIcon(String state) {
    switch (state) {
      case 'draft':
        return '📝';
      case 'confirm':
        return '⏳';
      case 'validate1':
        return '👁️';
      case 'validate':
        return '✅';
      case 'refuse':
        return '❌';
      case 'cancel':
        return '🚫';
      default:
        return '❓';
    }
  }

  static String _getStateColor(String state) {
    switch (state) {
      case 'draft':
        return '#9E9E9E';
      case 'confirm':
        return '#FFA500';
      case 'validate1':
        return '#2196F3';
      case 'validate':
        return '#4CAF50';
      case 'refuse':
        return '#F44336';
      case 'cancel':
        return '#9E9E9E';
      default:
        return '#9E9E9E';
    }
  }

  // تحديد ما إذا كان يمكن تنفيذ إجراءات معينة على الطلب
  bool canPerformAction(String action) {
    switch (action) {
      case 'edit':
        return state == 'draft';
      case 'submit':
        return state == 'draft';
      case 'cancel':
        return state == 'draft' || state == 'confirm';
      case 'approve':
        return state == 'confirm' || state == 'validate1';
      case 'refuse':
        return state == 'confirm' || state == 'validate1';
      default:
        return false;
    }
  }

  // الحصول على قائمة بالإجراءات المتاحة للطلب
  List<String> get availableActions {
    List<String> actions = [];

    if (canPerformAction('edit')) actions.add('edit');
    if (canPerformAction('submit')) actions.add('submit');
    if (canPerformAction('cancel')) actions.add('cancel');

    return actions;
  }

  // مقارنة طلبين حسب التاريخ
  int compareTo(LeaveRequest other) {
    return createdDate.compareTo(other.createdDate);
  }

  // فحص ما إذا كان الطلب يتداخل مع طلب آخر
  bool overlapsWith(LeaveRequest other) {
    return !(dateTo.isBefore(other.dateFrom) || dateFrom.isAfter(other.dateTo));
  }

  // حساب عدد أيام العمل الفعلية (باستثناء عطل نهاية الأسبوع)
  int get workingDaysCount {
    int workingDays = 0;
    DateTime current = dateFrom;

    while (current.isBefore(dateTo) || current.isAtSameMomentAs(dateTo)) {
      // تجاهل السبت (6) والأحد (7) - يمكن تعديلها حسب نظام العمل
      if (current.weekday != DateTime.saturday && current.weekday != DateTime.sunday) {
        workingDays++;
      }
      current = current.add(Duration(days: 1));
    }

    return workingDays;
  }

  @override
  String toString() {
    return 'LeaveRequest(id: $id, employeeId: $employeeId, type: $leaveTypeName, dates: ${formattedDateRange}, state: $stateText)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is LeaveRequest && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;
}