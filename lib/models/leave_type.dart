// lib/models/leave_type.dart - نموذج مُصحح
class LeaveType {
  final int id;
  final String name;
  final int maxDays;
  final String color;
  final bool requiresApproval;
  final String? description;
  final String timeType; // تم إضافة هذا
  final String allocationType; // تم إضافة هذا

  LeaveType({
    required this.id,
    required this.name,
    required this.maxDays,
    required this.color,
    required this.requiresApproval,
    this.description,
    this.timeType = 'leave', // قيمة افتراضية
    this.allocationType = 'no', // قيمة افتراضية
  });

  factory LeaveType.fromJson(Map<String, dynamic> json) {
    return LeaveType(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      maxDays: json['max_days'] ?? 0,
      color: json['color'] ?? '#2196F3',
      requiresApproval: json['requires_approval'] ?? true,
      description: json['description'],
      timeType: json['time_type'] ?? 'leave',
      allocationType: json['allocation_type'] ?? 'no',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'max_days': maxDays,
      'color': color,
      'requires_approval': requiresApproval,
      'description': description,
      'time_type': timeType,
      'allocation_type': allocationType,
    };
  }

  @override
  String toString() => name;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is LeaveType && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;
}