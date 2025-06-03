// lib/models/leave_stats.dart - إحصائيات الإجازات مُصححة
import 'leave_request.dart';

class LeaveStats {
  final int totalRequests;
  final int pendingRequests;
  final int approvedRequests;
  final int rejectedRequests;
  final int cancelledRequests;
  final double totalDaysUsed;
  final double totalDaysRemaining;
  final double totalDaysAllowed;
  final Map<String, int> leavesByType;
  final Map<String, double> daysByType;

  LeaveStats({
    required this.totalRequests,
    required this.pendingRequests,
    required this.approvedRequests,
    required this.rejectedRequests,
    required this.cancelledRequests,
    required this.totalDaysUsed,
    required this.totalDaysRemaining,
    required this.totalDaysAllowed,
    Map<String, int>? leavesByType,
    Map<String, double>? daysByType,
  }) :
        leavesByType = leavesByType ?? {},
        daysByType = daysByType ?? {};

  factory LeaveStats.fromRequests(List<LeaveRequest> requests, {double totalAllowed = 30}) {
    if (requests.isEmpty) {
      return LeaveStats(
        totalRequests: 0,
        pendingRequests: 0,
        approvedRequests: 0,
        rejectedRequests: 0,
        cancelledRequests: 0,
        totalDaysUsed: 0,
        totalDaysRemaining: totalAllowed,
        totalDaysAllowed: totalAllowed,
        leavesByType: {},
        daysByType: {},
      );
    }

    // تصنيف الطلبات
    final pending = requests.where((r) => r.isPending).toList();
    final approved = requests.where((r) => r.isApproved).toList();
    final rejected = requests.where((r) => r.isRejected).toList();
    final cancelled = requests.where((r) => r.isCancelled).toList();

    // حساب الأيام المستخدمة (فقط الطلبات المقبولة)
    final totalUsed = approved.fold<double>(0, (sum, r) => sum + r.numberOfDays);

    // إحصائيات حسب النوع
    Map<String, int> typeCount = {};
    Map<String, double> typeDays = {};

    for (final request in requests) {
      final typeName = request.leaveTypeName;

      // عدد الطلبات حسب النوع
      typeCount[typeName] = (typeCount[typeName] ?? 0) + 1;

      // الأيام حسب النوع (فقط المقبولة)
      if (request.isApproved) {
        typeDays[typeName] = (typeDays[typeName] ?? 0) + request.numberOfDays;
      }
    }

    return LeaveStats(
      totalRequests: requests.length,
      pendingRequests: pending.length,
      approvedRequests: approved.length,
      rejectedRequests: rejected.length,
      cancelledRequests: cancelled.length,
      totalDaysUsed: totalUsed,
      totalDaysRemaining: totalAllowed - totalUsed,
      totalDaysAllowed: totalAllowed,
      leavesByType: typeCount,
      daysByType: typeDays,
    );
  }

  // حساب النسب المئوية
  double get approvalRate {
    if (totalRequests == 0) return 0.0;
    return (approvedRequests / totalRequests) * 100;
  }

  double get pendingRate {
    if (totalRequests == 0) return 0.0;
    return (pendingRequests / totalRequests) * 100;
  }

  double get rejectionRate {
    if (totalRequests == 0) return 0.0;
    return (rejectedRequests / totalRequests) * 100;
  }

  double get cancellationRate {
    if (totalRequests == 0) return 0.0;
    return (cancelledRequests / totalRequests) * 100;
  }

  double get usageRate {
    if (totalDaysAllowed == 0) return 0.0;
    return (totalDaysUsed / totalDaysAllowed) * 100;
  }

  // الحصول على نوع الإجازة الأكثر استخداماً
  String? get mostUsedLeaveType {
    if (daysByType.isEmpty) return null;

    String? mostUsed;
    double maxDays = 0;

    daysByType.forEach((type, days) {
      if (days > maxDays) {
        maxDays = days;
        mostUsed = type;
      }
    });

    return mostUsed;
  }

  // الحصول على إجمالي الطلبات النشطة (المعلقة + المقبولة)
  int get activeRequests => pendingRequests + approvedRequests;

  // فحص ما إذا كان هناك رصيد كافي لإجازة جديدة
  bool canTakeLeave(double requestedDays) {
    return totalDaysRemaining >= requestedDays;
  }

  // الحصول على متوسط أيام الإجازة لكل طلب
  double get averageDaysPerRequest {
    if (totalRequests == 0) return 0.0;
    return totalDaysUsed / totalRequests;
  }

  // الحصول على الأيام المستخدمة لنوع معين
  double getDaysUsedForType(String leaveType) {
    return daysByType[leaveType] ?? 0.0;
  }

  // الحصول على عدد الطلبات لنوع معين
  int getRequestsCountForType(String leaveType) {
    return leavesByType[leaveType] ?? 0;
  }

  // إنشاء نسخة محدثة من الإحصائيات
  LeaveStats copyWith({
    int? totalRequests,
    int? pendingRequests,
    int? approvedRequests,
    int? rejectedRequests,
    int? cancelledRequests,
    double? totalDaysUsed,
    double? totalDaysRemaining,
    double? totalDaysAllowed,
    Map<String, int>? leavesByType,
    Map<String, double>? daysByType,
  }) {
    return LeaveStats(
      totalRequests: totalRequests ?? this.totalRequests,
      pendingRequests: pendingRequests ?? this.pendingRequests,
      approvedRequests: approvedRequests ?? this.approvedRequests,
      rejectedRequests: rejectedRequests ?? this.rejectedRequests,
      cancelledRequests: cancelledRequests ?? this.cancelledRequests,
      totalDaysUsed: totalDaysUsed ?? this.totalDaysUsed,
      totalDaysRemaining: totalDaysRemaining ?? this.totalDaysRemaining,
      totalDaysAllowed: totalDaysAllowed ?? this.totalDaysAllowed,
      leavesByType: leavesByType ?? Map.from(this.leavesByType),
      daysByType: daysByType ?? Map.from(this.daysByType),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_requests': totalRequests,
      'pending_requests': pendingRequests,
      'approved_requests': approvedRequests,
      'rejected_requests': rejectedRequests,
      'cancelled_requests': cancelledRequests,
      'total_days_used': totalDaysUsed,
      'total_days_remaining': totalDaysRemaining,
      'total_days_allowed': totalDaysAllowed,
      'approval_rate': approvalRate,
      'pending_rate': pendingRate,
      'rejection_rate': rejectionRate,
      'cancellation_rate': cancellationRate,
      'usage_rate': usageRate,
      'leaves_by_type': leavesByType,
      'days_by_type': daysByType,
      'most_used_leave_type': mostUsedLeaveType,
      'average_days_per_request': averageDaysPerRequest,
    };
  }

  factory LeaveStats.fromJson(Map<String, dynamic> json) {
    return LeaveStats(
      totalRequests: json['total_requests'] ?? 0,
      pendingRequests: json['pending_requests'] ?? 0,
      approvedRequests: json['approved_requests'] ?? 0,
      rejectedRequests: json['rejected_requests'] ?? 0,
      cancelledRequests: json['cancelled_requests'] ?? 0,
      totalDaysUsed: (json['total_days_used'] ?? 0).toDouble(),
      totalDaysRemaining: (json['total_days_remaining'] ?? 0).toDouble(),
      totalDaysAllowed: (json['total_days_allowed'] ?? 30).toDouble(),
      leavesByType: Map<String, int>.from(json['leaves_by_type'] ?? {}),
      daysByType: Map<String, double>.from(json['days_by_type'] ?? {}),
    );
  }

  // إحصائيات سريعة للعرض
  Map<String, dynamic> getQuickStats() {
    return {
      'total_requests': totalRequests,
      'pending_requests': pendingRequests,
      'days_used': totalDaysUsed.toStringAsFixed(1),
      'days_remaining': totalDaysRemaining.toStringAsFixed(1),
      'usage_percentage': usageRate.toStringAsFixed(1),
      'approval_percentage': approvalRate.toStringAsFixed(1),
    };
  }

  // التحقق من وجود طلبات معلقة
  bool get hasPendingRequests => pendingRequests > 0;

  // التحقق من استنفاد الرصيد
  bool get isQuotaExhausted => totalDaysRemaining <= 0;

  // التحقق من اقتراب استنفاد الرصيد (أقل من 20%)
  bool get isQuotaNearlyExhausted => (totalDaysRemaining / totalDaysAllowed) < 0.2;

  // الحصول على رسالة حالة الرصيد
  String get quotaStatusMessage {
    if (isQuotaExhausted) {
      return 'تم استنفاد رصيد الإجازات';
    } else if (isQuotaNearlyExhausted) {
      return 'رصيد الإجازات قارب على النفاد';
    } else {
      return 'رصيد الإجازات جيد';
    }
  }

  // الحصول على لون حالة الرصيد
  String get quotaStatusColor {
    if (isQuotaExhausted) {
      return '#F44336'; // أحمر
    } else if (isQuotaNearlyExhausted) {
      return '#FF9800'; // برتقالي
    } else {
      return '#4CAF50'; // أخضر
    }
  }

  @override
  String toString() {
    return 'LeaveStats(total: $totalRequests, approved: $approvedRequests, pending: $pendingRequests, rejected: $rejectedRequests, daysUsed: $totalDaysUsed/$totalDaysAllowed)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is LeaveStats &&
        other.totalRequests == totalRequests &&
        other.pendingRequests == pendingRequests &&
        other.approvedRequests == approvedRequests &&
        other.rejectedRequests == rejectedRequests &&
        other.totalDaysUsed == totalDaysUsed;
  }

  @override
  int get hashCode {
    return Object.hash(
      totalRequests,
      pendingRequests,
      approvedRequests,
      rejectedRequests,
      totalDaysUsed,
    );
  }
}