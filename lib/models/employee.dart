// lib/models/employee.dart - محدث مع دعم الصورة
class Employee {
  final int id;
  final String name;
  final String jobTitle;
  final String department;
  final String workEmail;
  final String workPhone;
  final String mobilePhone;
  final String? imageUrl; // إضافة رابط الصورة
  final String? avatar128; // صورة صغيرة 128x128
  final String? image1920; // صورة عالية الدقة

  Employee({
    required this.id,
    required this.name,
    required this.jobTitle,
    required this.department,
    required this.workEmail,
    this.workPhone = '',
    this.mobilePhone = '',
    this.imageUrl,
    this.avatar128,
    this.image1920,
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
    String? imageUrl,
    String? avatar128,
    String? image1920,
  }) {
    return Employee(
      id: id ?? this.id,
      name: name ?? this.name,
      jobTitle: jobTitle ?? this.jobTitle,
      department: department ?? this.department,
      workEmail: workEmail ?? this.workEmail,
      workPhone: workPhone ?? this.workPhone,
      mobilePhone: mobilePhone ?? this.mobilePhone,
      imageUrl: imageUrl ?? this.imageUrl,
      avatar128: avatar128 ?? this.avatar128,
      image1920: image1920 ?? this.image1920,
    );
  }

  // تحديد أفضل صورة متاحة
  String? get bestAvailableImage {
    if (avatar128 != null && avatar128!.isNotEmpty) return avatar128;
    if (image1920 != null && image1920!.isNotEmpty) return image1920;
    if (imageUrl != null && imageUrl!.isNotEmpty) return imageUrl;
    return null;
  }

  // التحقق من وجود صورة
  bool get hasImage => bestAvailableImage != null;

  // تحويل إلى JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'job_title': jobTitle,
      'department': department,
      'work_email': workEmail,
      'work_phone': workPhone,
      'mobile_phone': mobilePhone,
      'image_url': imageUrl,
      'avatar_128': avatar128,
      'image_1920': image1920,
    };
  }

  // إنشاء من JSON
  factory Employee.fromJson(Map<String, dynamic> json) {
    return Employee(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      jobTitle: json['job_title'] ?? json['jobTitle'] ?? '',
      department: json['department'] ?? '',
      workEmail: json['work_email'] ?? json['workEmail'] ?? '',
      workPhone: json['work_phone'] ?? json['workPhone'] ?? '',
      mobilePhone: json['mobile_phone'] ?? json['mobilePhone'] ?? '',
      imageUrl: json['image_url'] ?? json['imageUrl'],
      avatar128: json['avatar_128'] ?? json['avatar128'],
      image1920: json['image_1920'] ?? json['image1920'],
    );
  }

  @override
  String toString() {
    return 'Employee(id: $id, name: $name, jobTitle: $jobTitle, department: $department, hasImage: $hasImage)';
  }
}