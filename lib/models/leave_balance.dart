// lib/models/leave_balance.dart
class LeaveBalance {
  final int leaveTypeId;
  final String leaveTypeName;
  final double totalDays;
  final double usedDays;
  final double remainingDays;

  LeaveBalance({
    required this.leaveTypeId,
    required this.leaveTypeName,
    required this.totalDays,
    required this.usedDays,
    required this.remainingDays,
  });

  // نسبة الاستخدام
  double get usagePercentage {
    if (totalDays == 0) return 0;
    return (usedDays / totalDays) * 100;
  }

  // هل الرصيد منخفض؟
  bool get isLowBalance => remainingDays < (totalDays * 0.2);

  // هل الرصيد منتهي؟
  bool get isExhausted => remainingDays <= 0;

  Map<String, dynamic> toJson() {
    return {
      'leave_type_id': leaveTypeId,
      'leave_type_name': leaveTypeName,
      'total_days': totalDays,
      'used_days': usedDays,
      'remaining_days': remainingDays,
      'usage_percentage': usagePercentage,
    };
  }

  factory LeaveBalance.fromJson(Map<String, dynamic> json) {
    return LeaveBalance(
      leaveTypeId: json['leave_type_id'],
      leaveTypeName: json['leave_type_name'],
      totalDays: (json['total_days'] ?? 0).toDouble(),
      usedDays: (json['used_days'] ?? 0).toDouble(),
      remainingDays: (json['remaining_days'] ?? 0).toDouble(),
    );
  }
}