// models/leave_type.dart - نموذج نوع الإجازة
class LeaveType {
  final int id;
  final String name;
  final int maxDays;
  final String color;
  final bool requiresApproval;
  final String? description;

  LeaveType({
    required this.id,
    required this.name,
    required this.maxDays,
    required this.color,
    required this.requiresApproval,
    this.description,
  });

  factory LeaveType.fromJson(Map<String, dynamic> json) {
    return LeaveType(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      maxDays: json['max_days'] ?? 0,
      color: json['color'] ?? '#2196F3',
      requiresApproval: json['requires_approval'] ?? true,
      description: json['description'],
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