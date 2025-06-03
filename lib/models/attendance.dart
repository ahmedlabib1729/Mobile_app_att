// models/attendance.dart - نموذج بيانات الحضور مع دعم الموقع الجغرافي
import 'dart:convert';

class Attendance {
  final int id;
  final int employeeId;
  final DateTime checkIn;
  final DateTime? checkOut;
  final String? duration;

  // حقول الموقع الجديدة
  final double? checkInLatitude;
  final double? checkInLongitude;
  final double? checkOutLatitude;
  final double? checkOutLongitude;
  final double? checkInDistance; // المسافة من موقع العمل عند الحضور
  final double? checkOutDistance; // المسافة من موقع العمل عند الانصراف
  final bool? locationVerified; // هل تم التحقق من الموقع

  final bool isLocal;
  final bool isSynced;
  final DateTime createdAt;
  final DateTime? updatedAt;

  Attendance({
    required this.id,
    required this.employeeId,
    required this.checkIn,
    this.checkOut,
    this.duration,
    this.checkInLatitude,
    this.checkInLongitude,
    this.checkOutLatitude,
    this.checkOutLongitude,
    this.checkInDistance,
    this.checkOutDistance,
    this.locationVerified,
    this.isLocal = false,
    this.isSynced = true,
    required this.createdAt,
    this.updatedAt,
  });

  // نسخ الحضور مع تحديث بعض القيم
  Attendance copyWith({
    int? id,
    int? employeeId,
    DateTime? checkIn,
    DateTime? checkOut,
    String? duration,
    double? checkInLatitude,
    double? checkInLongitude,
    double? checkOutLatitude,
    double? checkOutLongitude,
    double? checkInDistance,
    double? checkOutDistance,
    bool? locationVerified,
    bool? isLocal,
    bool? isSynced,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Attendance(
      id: id ?? this.id,
      employeeId: employeeId ?? this.employeeId,
      checkIn: checkIn ?? this.checkIn,
      checkOut: checkOut ?? this.checkOut,
      duration: duration ?? this.duration,
      checkInLatitude: checkInLatitude ?? this.checkInLatitude,
      checkInLongitude: checkInLongitude ?? this.checkInLongitude,
      checkOutLatitude: checkOutLatitude ?? this.checkOutLatitude,
      checkOutLongitude: checkOutLongitude ?? this.checkOutLongitude,
      checkInDistance: checkInDistance ?? this.checkInDistance,
      checkOutDistance: checkOutDistance ?? this.checkOutDistance,
      locationVerified: locationVerified ?? this.locationVerified,
      isLocal: isLocal ?? this.isLocal,
      isSynced: isSynced ?? this.isSynced,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  // حساب مدة العمل
  String calculateDuration() {
    if (checkOut == null) {
      final now = DateTime.now();
      final workDuration = now.difference(checkIn);
      return _formatDuration(workDuration);
    } else {
      final workDuration = checkOut!.difference(checkIn);
      return _formatDuration(workDuration);
    }
  }

  // تنسيق المدة
  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes % 60;
    return '$hours:${minutes.toString().padLeft(2, '0')}';
  }

  // الحصول على موقع الحضور كنص
  String? get checkInLocationText {
    if (checkInLatitude != null && checkInLongitude != null) {
      return '${checkInLatitude!.toStringAsFixed(4)}, ${checkInLongitude!.toStringAsFixed(4)}';
    }
    return null;
  }

  // الحصول على موقع الانصراف كنص
  String? get checkOutLocationText {
    if (checkOutLatitude != null && checkOutLongitude != null) {
      return '${checkOutLatitude!.toStringAsFixed(4)}, ${checkOutLongitude!.toStringAsFixed(4)}';
    }
    return null;
  }

  // تنسيق المسافة للعرض
  String? formatDistance(double? distance) {
    if (distance == null) return null;
    if (distance < 1000) {
      return '${distance.round()} متر';
    } else {
      return '${(distance / 1000).toStringAsFixed(1)} كم';
    }
  }

  // الحصول على التاريخ كنص منسق
  String getFormattedDate() {
    const List<String> months = [
      'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
      'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ];

    const List<String> weekdays = [
      'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'
    ];

    final date = checkIn;
    final weekday = weekdays[date.weekday - 1];
    final day = date.day;
    final month = months[date.month - 1];
    final year = date.year;

    return '$weekday، $day $month $year';
  }

  // الحصول على وقت الحضور منسق
  String getFormattedCheckIn() {
    return '${checkIn.hour.toString().padLeft(2, '0')}:${checkIn.minute.toString().padLeft(2, '0')}';
  }

  // الحصول على وقت الانصراف منسق
  String? getFormattedCheckOut() {
    if (checkOut == null) return null;
    return '${checkOut!.hour.toString().padLeft(2, '0')}:${checkOut!.minute.toString().padLeft(2, '0')}';
  }

  // التحقق من أن اليوم هو اليوم الحالي
  bool isToday() {
    final now = DateTime.now();
    return checkIn.year == now.year &&
        checkIn.month == now.month &&
        checkIn.day == now.day;
  }

  // التحقق من أن الحضور ما زال مفتوحاً
  bool get isActive => checkOut == null;

  // الحصول على حالة الحضور
  AttendanceStatus get status {
    if (checkOut == null) {
      return AttendanceStatus.active;
    } else if (!isSynced) {
      return AttendanceStatus.pendingSync;
    } else {
      return AttendanceStatus.completed;
    }
  }

  // التحقق من صحة الموقع
  bool get hasValidLocation {
    return (checkInLatitude != null && checkInLongitude != null) ||
        (checkOutLatitude != null && checkOutLongitude != null);
  }

  // تحويل إلى JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'employee_id': employeeId,
      'check_in': checkIn.toIso8601String(),
      'check_out': checkOut?.toIso8601String(),
      'duration': duration ?? calculateDuration(),
      'check_in_latitude': checkInLatitude,
      'check_in_longitude': checkInLongitude,
      'check_out_latitude': checkOutLatitude,
      'check_out_longitude': checkOutLongitude,
      'check_in_distance': checkInDistance,
      'check_out_distance': checkOutDistance,
      'location_verified': locationVerified,
      'is_local': isLocal,
      'is_synced': isSynced,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  // إنشاء من JSON
  factory Attendance.fromJson(Map<String, dynamic> json) {
    return Attendance(
      id: json['id'] ?? 0,
      employeeId: json['employee_id'] ?? json['employeeId'] ?? 0,
      checkIn: DateTime.parse(json['check_in'] ?? json['checkIn']),
      checkOut: json['check_out'] != null || json['checkOut'] != null
          ? DateTime.parse(json['check_out'] ?? json['checkOut'])
          : null,
      duration: json['duration'],
      checkInLatitude: json['check_in_latitude']?.toDouble(),
      checkInLongitude: json['check_in_longitude']?.toDouble(),
      checkOutLatitude: json['check_out_latitude']?.toDouble(),
      checkOutLongitude: json['check_out_longitude']?.toDouble(),
      checkInDistance: json['check_in_distance']?.toDouble(),
      checkOutDistance: json['check_out_distance']?.toDouble(),
      locationVerified: json['location_verified'],
      isLocal: json['is_local'] ?? json['isLocal'] ?? false,
      isSynced: json['is_synced'] ?? json['isSynced'] ?? true,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
    );
  }

  // تحويل إلى Map للعرض في الواجهة
  Map<String, dynamic> toDisplayMap() {
    return {
      'id': id.toString(),
      'date': getFormattedDate(),
      'checkIn': getFormattedCheckIn(),
      'checkOut': getFormattedCheckOut() ?? 'لم يسجل',
      'duration': duration ?? calculateDuration(),
      'check_in_location': checkInLocationText,
      'check_out_location': checkOutLocationText,
      'check_in_distance': formatDistance(checkInDistance),
      'check_out_distance': formatDistance(checkOutDistance),
      'location_verified': locationVerified,
      'status': _getStatusText(),
      'isLocal': isLocal,
      'isSynced': isSynced,
    };
  }

  // الحصول على نص الحالة
  String _getStatusText() {
    switch (status) {
      case AttendanceStatus.active:
        return 'نشط';
      case AttendanceStatus.completed:
        return 'مكتمل';
      case AttendanceStatus.pendingSync:
        return 'في انتظار المزامنة';
    }
  }

  @override
  String toString() {
    return 'Attendance(id: $id, employeeId: $employeeId, checkIn: $checkIn, checkOut: $checkOut, '
        'checkInLocation: $checkInLocationText, checkOutLocation: $checkOutLocationText, '
        'duration: ${duration ?? calculateDuration()}, isLocal: $isLocal, isSynced: $isSynced)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Attendance &&
        other.id == id &&
        other.employeeId == employeeId &&
        other.checkIn == checkIn &&
        other.checkOut == checkOut;
  }

  @override
  int get hashCode {
    return Object.hash(id, employeeId, checkIn, checkOut);
  }
}

// تعداد حالات الحضور
enum AttendanceStatus {
  active,
  completed,
  pendingSync,
}

// فئة لإدارة إحصائيات الحضور
class AttendanceStats {
  final int totalDays;
  final int presentDays;
  final int absentDays;
  final Duration totalWorkTime;
  final Duration averageWorkTime;
  final int lateArrivals;
  final int earlyDepartures;
  final int locationVerifiedCount; // عدد مرات التحقق من الموقع بنجاح
  final int locationFailedCount; // عدد مرات فشل التحقق من الموقع

  AttendanceStats({
    required this.totalDays,
    required this.presentDays,
    required this.absentDays,
    required this.totalWorkTime,
    required this.averageWorkTime,
    required this.lateArrivals,
    required this.earlyDepartures,
    this.locationVerifiedCount = 0,
    this.locationFailedCount = 0,
  });

  // حساب نسبة الحضور
  double get attendanceRate {
    if (totalDays == 0) return 0.0;
    return (presentDays / totalDays) * 100;
  }

  // حساب نسبة التحقق من الموقع
  double get locationVerificationRate {
    final total = locationVerifiedCount + locationFailedCount;
    if (total == 0) return 0.0;
    return (locationVerifiedCount / total) * 100;
  }

  // حساب متوسط ساعات العمل اليومي
  String get averageWorkTimeFormatted {
    final hours = averageWorkTime.inHours;
    final minutes = averageWorkTime.inMinutes % 60;
    return '$hours:${minutes.toString().padLeft(2, '0')}';
  }

  // حساب إجمالي ساعات العمل
  String get totalWorkTimeFormatted {
    final hours = totalWorkTime.inHours;
    final minutes = totalWorkTime.inMinutes % 60;
    return '$hours:${minutes.toString().padLeft(2, '0')}';
  }

  // تحويل إلى JSON
  Map<String, dynamic> toJson() {
    return {
      'total_days': totalDays,
      'present_days': presentDays,
      'absent_days': absentDays,
      'total_work_time_minutes': totalWorkTime.inMinutes,
      'average_work_time_minutes': averageWorkTime.inMinutes,
      'late_arrivals': lateArrivals,
      'early_departures': earlyDepartures,
      'location_verified_count': locationVerifiedCount,
      'location_failed_count': locationFailedCount,
      'attendance_rate': attendanceRate,
      'location_verification_rate': locationVerificationRate,
    };
  }

  // إنشاء من JSON
  factory AttendanceStats.fromJson(Map<String, dynamic> json) {
    return AttendanceStats(
      totalDays: json['total_days'] ?? 0,
      presentDays: json['present_days'] ?? 0,
      absentDays: json['absent_days'] ?? 0,
      totalWorkTime: Duration(minutes: json['total_work_time_minutes'] ?? 0),
      averageWorkTime: Duration(minutes: json['average_work_time_minutes'] ?? 0),
      lateArrivals: json['late_arrivals'] ?? 0,
      earlyDepartures: json['early_departures'] ?? 0,
      locationVerifiedCount: json['location_verified_count'] ?? 0,
      locationFailedCount: json['location_failed_count'] ?? 0,
    );
  }

  // حساب الإحصائيات من قائمة الحضور
  factory AttendanceStats.fromAttendanceList(List<Attendance> attendances) {
    if (attendances.isEmpty) {
      return AttendanceStats(
        totalDays: 0,
        presentDays: 0,
        absentDays: 0,
        totalWorkTime: Duration.zero,
        averageWorkTime: Duration.zero,
        lateArrivals: 0,
        earlyDepartures: 0,
        locationVerifiedCount: 0,
        locationFailedCount: 0,
      );
    }

    final presentDays = attendances.length;
    Duration totalWorkTime = Duration.zero;
    int lateArrivals = 0;
    int earlyDepartures = 0;
    int locationVerifiedCount = 0;
    int locationFailedCount = 0;

    // وقت الدوام المعياري (9:00 صباحاً - 5:00 مساءً)
    const standardStartHour = 9;
    const standardEndHour = 17;

    for (final attendance in attendances) {
      // حساب إجمالي وقت العمل
      if (attendance.checkOut != null) {
        final workDuration = attendance.checkOut!.difference(attendance.checkIn);
        totalWorkTime = Duration(minutes: totalWorkTime.inMinutes + workDuration.inMinutes);
      }

      // فحص التأخير (الوصول بعد 9:15 صباحاً)
      if (attendance.checkIn.hour > standardStartHour ||
          (attendance.checkIn.hour == standardStartHour && attendance.checkIn.minute > 15)) {
        lateArrivals++;
      }

      // فحص المغادرة المبكرة (قبل 4:45 مساءً)
      if (attendance.checkOut != null) {
        if (attendance.checkOut!.hour < standardEndHour ||
            (attendance.checkOut!.hour == standardEndHour && attendance.checkOut!.minute < 45)) {
          earlyDepartures++;
        }
      }

      // إحصائيات الموقع
      if (attendance.locationVerified == true) {
        locationVerifiedCount++;
      } else if (attendance.locationVerified == false) {
        locationFailedCount++;
      }
    }

    final averageWorkTime = presentDays > 0
        ? Duration(minutes: totalWorkTime.inMinutes ~/ presentDays)
        : Duration.zero;

    return AttendanceStats(
      totalDays: presentDays,
      presentDays: presentDays,
      absentDays: 0,
      totalWorkTime: totalWorkTime,
      averageWorkTime: averageWorkTime,
      lateArrivals: lateArrivals,
      earlyDepartures: earlyDepartures,
      locationVerifiedCount: locationVerifiedCount,
      locationFailedCount: locationFailedCount,
    );
  }

  @override
  String toString() {
    return 'AttendanceStats(totalDays: $totalDays, presentDays: $presentDays, '
        'attendanceRate: ${attendanceRate.toStringAsFixed(1)}%, '
        'locationVerificationRate: ${locationVerificationRate.toStringAsFixed(1)}%, '
        'totalWorkTime: $totalWorkTimeFormatted)';
  }
}

// فئة مساعدة لتصفية سجلات الحضور
class AttendanceFilter {
  final DateTime? startDate;
  final DateTime? endDate;
  final AttendanceStatus? status;
  final bool? isLocal;
  final bool? locationVerified; // فلتر جديد للموقع

  AttendanceFilter({
    this.startDate,
    this.endDate,
    this.status,
    this.isLocal,
    this.locationVerified,
  });

  // تطبيق التصفية على قائمة الحضور
  List<Attendance> apply(List<Attendance> attendances) {
    return attendances.where((attendance) {
      // تصفية بالتاريخ
      if (startDate != null && attendance.checkIn.isBefore(startDate!)) {
        return false;
      }
      if (endDate != null && attendance.checkIn.isAfter(endDate!.add(Duration(days: 1)))) {
        return false;
      }

      // تصفية بالحالة
      if (status != null && attendance.status != status) {
        return false;
      }

      // تصفية بالنوع (محلي/مزامن)
      if (isLocal != null && attendance.isLocal != isLocal) {
        return false;
      }

      // تصفية بالتحقق من الموقع
      if (locationVerified != null && attendance.locationVerified != locationVerified) {
        return false;
      }

      return true;
    }).toList();
  }

  // إنشاء مرشح للأسبوع الحالي
  factory AttendanceFilter.thisWeek() {
    final now = DateTime.now();
    final startOfWeek = now.subtract(Duration(days: now.weekday - 1));
    final endOfWeek = startOfWeek.add(Duration(days: 6));

    return AttendanceFilter(
      startDate: DateTime(startOfWeek.year, startOfWeek.month, startOfWeek.day),
      endDate: DateTime(endOfWeek.year, endOfWeek.month, endOfWeek.day),
    );
  }

  // إنشاء مرشح للشهر الحالي
  factory AttendanceFilter.thisMonth() {
    final now = DateTime.now();
    final startOfMonth = DateTime(now.year, now.month, 1);
    final endOfMonth = DateTime(now.year, now.month + 1, 0);

    return AttendanceFilter(
      startDate: startOfMonth,
      endDate: endOfMonth,
    );
  }

  // إنشاء مرشح للسجلات غير المزامنة
  factory AttendanceFilter.pendingSync() {
    return AttendanceFilter(
      status: AttendanceStatus.pendingSync,
    );
  }

  // إنشاء مرشح للسجلات المتحقق من موقعها
  factory AttendanceFilter.locationVerified() {
    return AttendanceFilter(
      locationVerified: true,
    );
  }

  // إنشاء مرشح للسجلات غير المتحقق من موقعها
  factory AttendanceFilter.locationNotVerified() {
    return AttendanceFilter(
      locationVerified: false,
    );
  }
}