// models/appointment.dart

class Appointment {
  final String id;
  final String title;
  final String description;
  final DateTime dateTime;
  final bool isNotificationEnabled;
  final int notificationMinutesBefore; // التنبيه قبل الموعد بكام دقيقة
  final String? location;
  final String? notes;
  final int colorIndex; // لون الموعد في التقويم
  final bool isCompleted;

  Appointment({
    required this.id,
    required this.title,
    required this.description,
    required this.dateTime,
    this.isNotificationEnabled = true,
    this.notificationMinutesBefore = 15,
    this.location,
    this.notes,
    this.colorIndex = 0,
    this.isCompleted = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'dateTime': dateTime.toIso8601String(),
      'isNotificationEnabled': isNotificationEnabled,
      'notificationMinutesBefore': notificationMinutesBefore,
      'location': location,
      'notes': notes,
      'colorIndex': colorIndex,
      'isCompleted': isCompleted,
    };
  }

  factory Appointment.fromJson(Map<String, dynamic> json) {
    return Appointment(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      dateTime: DateTime.parse(json['dateTime']),
      isNotificationEnabled: json['isNotificationEnabled'] ?? true,
      notificationMinutesBefore: json['notificationMinutesBefore'] ?? 15,
      location: json['location'],
      notes: json['notes'],
      colorIndex: json['colorIndex'] ?? 0,
      isCompleted: json['isCompleted'] ?? false,
    );
  }

  Appointment copyWith({
    String? id,
    String? title,
    String? description,
    DateTime? dateTime,
    bool? isNotificationEnabled,
    int? notificationMinutesBefore,
    String? location,
    String? notes,
    int? colorIndex,
    bool? isCompleted,
  }) {
    return Appointment(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      dateTime: dateTime ?? this.dateTime,
      isNotificationEnabled: isNotificationEnabled ?? this.isNotificationEnabled,
      notificationMinutesBefore: notificationMinutesBefore ?? this.notificationMinutesBefore,
      location: location ?? this.location,
      notes: notes ?? this.notes,
      colorIndex: colorIndex ?? this.colorIndex,
      isCompleted: isCompleted ?? this.isCompleted,
    );
  }
}