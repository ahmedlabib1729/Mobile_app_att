// models/leave_stats.dart - إحصائيات الإجازات
import 'leave_request.dart';

class LeaveStats {
  final int totalRequests;
  final int pendingRequests;
  final int approvedRequests;
  final int rejectedRequests;
  final double totalDaysUsed;
  final double totalDaysRemaining;

  LeaveStats({
    required this.totalRequests,
    required this.pendingRequests,
    required this.approvedRequests,
    required this.rejectedRequests,
    required this.totalDaysUsed,
    required this.totalDaysRemaining,
  });

  factory LeaveStats.fromRequests(List<LeaveRequest> requests) {
    final approved = requests.where((r) => r.isApproved).toList();
    final totalUsed = approved.fold<double>(0, (sum, r) => sum + r.numberOfDays);

    return LeaveStats(
      totalRequests: requests.length,
      pendingRequests: requests.where((r) => r.isPending).length,
      approvedRequests: approved.length,
      rejectedRequests: requests.where((r) => r.isRejected).length,
      totalDaysUsed: totalUsed,
      totalDaysRemaining: 30 - totalUsed, // افتراضي 30 يوم سنوياً
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

  Map<String, dynamic> toJson() {
    return {
      'total_requests': totalRequests,
      'pending_requests': pendingRequests,
      'approved_requests': approvedRequests,
      'rejected_requests': rejectedRequests,
      'total_days_used': totalDaysUsed,
      'total_days_remaining': totalDaysRemaining,
      'approval_rate': approvalRate,
      'pending_rate': pendingRate,
      'rejection_rate': rejectionRate,
    };
  }

  @override
  String toString() {
    return 'LeaveStats(total: $totalRequests, approved: $approvedRequests, pending: $pendingRequests, rejected: $rejectedRequests)';
  }
}