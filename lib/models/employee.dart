// employee.dart
class Employee {
  final int id;
  final String name;
  final String jobTitle;
  final String department;
  final String workEmail;
  final String workPhone;
  final String mobilePhone;

  Employee({
    required this.id,
    required this.name,
    required this.jobTitle,
    required this.department,
    required this.workEmail,
    this.workPhone = '',
    this.mobilePhone = '',
  });

  // نسخ الموظف مع تحديث بعض القيم
  Employee copyWith({
    int? id,
    String? name,
    String? jobTitle,
    String? department,
    String? workEmail,
    String? workPhone,
    String? mobilePhone,
  }) {
    return Employee(
      id: id ?? this.id,
      name: name ?? this.name,
      jobTitle: jobTitle ?? this.jobTitle,
      department: department ?? this.department,
      workEmail: workEmail ?? this.workEmail,
      workPhone: workPhone ?? this.workPhone,
      mobilePhone: mobilePhone ?? this.mobilePhone,
    );
  }

  @override
  String toString() {
    return 'Employee(id: $id, name: $name, jobTitle: $jobTitle, department: $department)';
  }
}