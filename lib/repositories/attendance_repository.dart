// repositories/attendance_repository.dart - مستودع إدارة بيانات الحضور
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/attendance.dart';
import '../services/odoo_service.dart';
import '../services/cache_manager.dart';
import '../utils/exceptions.dart';

class AttendanceRepository {
  static final AttendanceRepository _instance = AttendanceRepository._internal();
  factory AttendanceRepository() => _instance;
  AttendanceRepository._internal();

  final OdooService _odooService = OdooService(url: '', database: '');

  // مفاتيح التخزين المحلي
  static const String _attendanceKey = 'attendance_records';
  static const String _currentAttendanceKey = 'current_attendance';
  static const String _statsKey = 'attendance_stats';

  // الحصول على جميع سجلات الحضور للموظف
  Future<List<Attendance>> getAttendanceRecords(int employeeId, {
    AttendanceFilter? filter,
    bool includeLocal = true,
  }) async {
    try {
      List<Attendance> records = [];

      // جلب السجلات من الخادم
      try {
        final serverRecords = await _getServerRecords(employeeId);
        records.addAll(serverRecords);
      } catch (e) {
        print('فشل جلب السجلات من الخادم: $e');
      }

      // إضافة السجلات المحلية إذا كان مطلوباً
      if (includeLocal) {
        final localRecords = await _getLocalRecords(employeeId);
        records.addAll(localRecords);
      }

      // إزالة المكررات (السجلات المزامنة)
      records = _removeDuplicates(records);

      // ترتيب حسب التاريخ (الأحدث أولاً)
      records.sort((a, b) => b.checkIn.compareTo(a.checkIn));

      // تطبيق التصفية إذا كانت موجودة
      if (filter != null) {
        records = filter.apply(records);
      }

      return records;
    } catch (e) {
      throw DataNotFoundException('فشل في جلب سجلات الحضور: $e');
    }
  }

  // الحصول على سجلات الحضور من الخادم
  Future<List<Attendance>> _getServerRecords(int employeeId) async {
    try {
      final response = await _odooService.getAttendanceHistory(employeeId);

      return response.map((record) {
        return Attendance.fromJson({
          ...record,
          'is_local': false,
          'is_synced': true,
        });
      }).toList();
    } catch (e) {
      throw ServerException('فشل جلب السجلات من الخادم: $e');
    }
  }

  // الحصول على السجلات المحلية
  Future<List<Attendance>> _getLocalRecords(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final recordsKey = '${_attendanceKey}_$employeeId';
      final recordsJson = prefs.getStringList(recordsKey) ?? [];

      return recordsJson.map((recordJson) {
        final data = jsonDecode(recordJson);
        return Attendance.fromJson(data);
      }).toList();
    } catch (e) {
      print('خطأ في جلب السجلات المحلية: $e');
      return [];
    }
  }

  // إزالة السجلات المكررة
  List<Attendance> _removeDuplicates(List<Attendance> records) {
    final Map<String, Attendance> uniqueRecords = {};

    for (final record in records) {
      // استخدام التاريخ كمفتاح فريد
      final key = '${record.employeeId}_${record.checkIn.year}_${record.checkIn.month}_${record.checkIn.day}';

      // الاحتفاظ بالسجل المزامن إذا كان موجوداً
      if (!uniqueRecords.containsKey(key) ||
          (uniqueRecords[key]!.isLocal && !record.isLocal)) {
        uniqueRecords[key] = record;
      }
    }

    return uniqueRecords.values.toList();
  }

  // حفظ سجل حضور جديد محلياً
  Future<Attendance> saveLocalAttendance(Attendance attendance) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final recordsKey = '${_attendanceKey}_${attendance.employeeId}';

      // الحصول على السجلات الموجودة
      List<String> existingRecords = prefs.getStringList(recordsKey) ?? [];

      // إضافة السجل الجديد
      final newRecord = attendance.copyWith(
        isLocal: true,
        isSynced: false,
        createdAt: DateTime.now(),
      );

      existingRecords.insert(0, jsonEncode(newRecord.toJson()));

      // الاحتفاظ بأحدث 100 سجل فقط
      if (existingRecords.length > 100) {
        existingRecords = existingRecords.take(100).toList();
      }

      await prefs.setStringList(recordsKey, existingRecords);

      print('تم حفظ سجل الحضور محلياً للموظف ${attendance.employeeId}');
      return newRecord;
    } catch (e) {
      throw Exception('فشل في حفظ سجل الحضور محلياً: $e');
    }
  }

  // تحديث سجل حضور محلي
  Future<void> updateLocalAttendance(Attendance attendance) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final recordsKey = '${_attendanceKey}_${attendance.employeeId}';

      List<String> existingRecords = prefs.getStringList(recordsKey) ?? [];

      // البحث عن السجل وتحديثه
      for (int i = 0; i < existingRecords.length; i++) {
        final recordData = jsonDecode(existingRecords[i]);
        final existingAttendance = Attendance.fromJson(recordData);

        if (existingAttendance.id == attendance.id) {
          final updatedAttendance = attendance.copyWith(
            updatedAt: DateTime.now(),
          );
          existingRecords[i] = jsonEncode(updatedAttendance.toJson());
          break;
        }
      }

      await prefs.setStringList(recordsKey, existingRecords);
      print('تم تحديث سجل الحضور محلياً');
    } catch (e) {
      throw Exception('فشل في تحديث سجل الحضور محلياً: $e');
    }
  }

  // الحصول على الحضور النشط الحالي
  Future<Attendance?> getCurrentAttendance(int employeeId) async {
    try {
      // البحث في السجلات النشطة
      final records = await getAttendanceRecords(employeeId);

      // العثور على أول سجل نشط (بدون انصراف)
      for (final record in records) {
        if (record.isActive && record.isToday()) {
          return record;
        }
      }

      return null;
    } catch (e) {
      print('خطأ في جلب الحضور الحالي: $e');
      return null;
    }
  }

  // تسجيل حضور جديد
  Future<Attendance> checkIn(int employeeId) async {
    try {
      final now = DateTime.now();

      // التحقق من عدم وجود حضور نشط
      final currentAttendance = await getCurrentAttendance(employeeId);
      if (currentAttendance != null) {
        throw ValidationException('يوجد حضور نشط بالفعل');
      }

      // إنشاء سجل حضور جديد
      final attendance = Attendance(
        id: now.millisecondsSinceEpoch, // ID مؤقت للسجل المحلي
        employeeId: employeeId,
        checkIn: now,
        isLocal: true,
        isSynced: false,
        createdAt: now,
      );

      // حفظ محلياً
      final savedAttendance = await saveLocalAttendance(attendance);

      // حفظ كحضور حالي
      await _saveCurrentAttendance(savedAttendance);

      return savedAttendance;
    } catch (e) {
      if (e is AppException) rethrow;
      throw ServerException('فشل في تسجيل الحضور: $e');
    }
  }

  // تسجيل انصراف
  Future<Attendance> checkOut(int employeeId) async {
    try {
      final now = DateTime.now();

      // الحصول على الحضور النشط
      final currentAttendance = await getCurrentAttendance(employeeId);
      if (currentAttendance == null) {
        throw ValidationException('لا يوجد حضور نشط للانصراف منه');
      }

      // تحديث الحضور بوقت الانصراف
      final updatedAttendance = currentAttendance.copyWith(
        checkOut: now,
        updatedAt: now,
      );

      // تحديث السجل محلياً
      await updateLocalAttendance(updatedAttendance);

      // إزالة الحضور الحالي
      await _clearCurrentAttendance(employeeId);

      return updatedAttendance;
    } catch (e) {
      if (e is AppException) rethrow;
      throw ServerException('فشل في تسجيل الانصراف: $e');
    }
  }

  // حفظ الحضور الحالي
  Future<void> _saveCurrentAttendance(Attendance attendance) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = '${_currentAttendanceKey}_${attendance.employeeId}';
      await prefs.setString(key, jsonEncode(attendance.toJson()));
    } catch (e) {
      print('خطأ في حفظ الحضور الحالي: $e');
    }
  }

  // مسح الحضور الحالي
  Future<void> _clearCurrentAttendance(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = '${_currentAttendanceKey}_$employeeId';
      await prefs.remove(key);
    } catch (e) {
      print('خطأ في مسح الحضور الحالي: $e');
    }
  }

  // حساب إحصائيات الحضور
  Future<AttendanceStats> getAttendanceStats(int employeeId, {
    AttendanceFilter? filter,
  }) async {
    try {
      final records = await getAttendanceRecords(employeeId, filter: filter);

      // حساب الإحصائيات من السجلات
      final stats = AttendanceStats.fromAttendanceList(records);

      // حفظ الإحصائيات في الكاش
      await _cacheStats(employeeId, stats);

      return stats;
    } catch (e) {
      // في حالة الفشل، محاولة استرجاع الإحصائيات المحفوظة
      final cachedStats = await _getCachedStats(employeeId);
      if (cachedStats != null) {
        return cachedStats;
      }

      throw DataNotFoundException('فشل في حساب إحصائيات الحضور: $e');
    }
  }

  // حفظ الإحصائيات في الكاش
  Future<void> _cacheStats(int employeeId, AttendanceStats stats) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = '${_statsKey}_$employeeId';
      await prefs.setString(key, jsonEncode(stats.toJson()));
    } catch (e) {
      print('خطأ في حفظ الإحصائيات: $e');
    }
  }

  // استرجاع الإحصائيات المحفوظة
  Future<AttendanceStats?> _getCachedStats(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = '${_statsKey}_$employeeId';
      final statsJson = prefs.getString(key);

      if (statsJson != null) {
        final data = jsonDecode(statsJson);
        return AttendanceStats.fromJson(data);
      }

      return null;
    } catch (e) {
      print('خطأ في استرجاع الإحصائيات المحفوظة: $e');
      return null;
    }
  }

  // مزامنة السجلات المحلية مع الخادم
  Future<void> syncLocalRecords(int employeeId) async {
    try {
      print('بدء مزامنة سجلات الحضور للموظف $employeeId');

      // الحصول على السجلات غير المزامنة
      final localRecords = await _getLocalRecords(employeeId);
      final unSyncedRecords = localRecords.where((record) => !record.isSynced).toList();

      if (unSyncedRecords.isEmpty) {
        print('لا توجد سجلات تحتاج مزامنة');
        return;
      }

      print('عدد السجلات المراد مزامنتها: ${unSyncedRecords.length}');

      for (final record in unSyncedRecords) {
        try {
          // رفع السجل للخادم
          Map<String, dynamic> result;

          if (record.checkOut == null) {
            // تسجيل حضور
            result = await _odooService.checkIn(employeeId);
          } else {
            // تسجيل حضور وانصراف
            await _odooService.checkIn(employeeId);
            result = await _odooService.checkOut(employeeId);
          }

          if (result['success'] == true) {
            // تحديث السجل كمزامن
            final syncedRecord = record.copyWith(
              isSynced: true,
              isLocal: false,
              updatedAt: DateTime.now(),
            );

            await updateLocalAttendance(syncedRecord);
            print('تمت مزامنة سجل بتاريخ ${record.getFormattedDate()}');
          }

        } catch (e) {
          print('فشل في مزامنة سجل ${record.id}: $e');
          // الاستمرار مع السجلات الأخرى
        }
      }

      print('اكتملت مزامنة سجلات الحضور');
    } catch (e) {
      throw ServerException('فشل في مزامنة السجلات المحلية: $e');
    }
  }

  // حذف سجل حضور محلي
  Future<void> deleteLocalRecord(int employeeId, int recordId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final recordsKey = '${_attendanceKey}_$employeeId';

      List<String> existingRecords = prefs.getStringList(recordsKey) ?? [];

      // إزالة السجل المطلوب
      existingRecords.removeWhere((recordJson) {
        final data = jsonDecode(recordJson);
        return data['id'] == recordId;
      });

      await prefs.setStringList(recordsKey, existingRecords);
      print('تم حذف سجل الحضور $recordId محلياً');
    } catch (e) {
      throw Exception('فشل في حذف سجل الحضور: $e');
    }
  }

  // تنظيف السجلات القديمة
  Future<void> cleanupOldRecords(int employeeId, {int keepDays = 90}) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final recordsKey = '${_attendanceKey}_$employeeId';

      List<String> existingRecords = prefs.getStringList(recordsKey) ?? [];
      final cutoffDate = DateTime.now().subtract(Duration(days: keepDays));

      // فلترة السجلات للاحتفاظ بالحديثة فقط
      final filteredRecords = existingRecords.where((recordJson) {
        try {
          final data = jsonDecode(recordJson);
          final attendance = Attendance.fromJson(data);
          return attendance.checkIn.isAfter(cutoffDate);
        } catch (e) {
          return false; // إزالة السجلات التالفة
        }
      }).toList();

      if (filteredRecords.length != existingRecords.length) {
        await prefs.setStringList(recordsKey, filteredRecords);
        print('تم تنظيف ${existingRecords.length - filteredRecords.length} سجل قديم');
      }
    } catch (e) {
      print('خطأ في تنظيف السجلات القديمة: $e');
    }
  }

  // الحصول على سجلات اليوم
  Future<List<Attendance>> getTodayRecords(int employeeId) async {
    final filter = AttendanceFilter(
      startDate: DateTime.now(),
      endDate: DateTime.now(),
    );

    return await getAttendanceRecords(employeeId, filter: filter);
  }

  // الحصول على سجلات الأسبوع الحالي
  Future<List<Attendance>> getThisWeekRecords(int employeeId) async {
    final filter = AttendanceFilter.thisWeek();
    return await getAttendanceRecords(employeeId, filter: filter);
  }

  // الحصول على سجلات الشهر الحالي
  Future<List<Attendance>> getThisMonthRecords(int employeeId) async {
    final filter = AttendanceFilter.thisMonth();
    return await getAttendanceRecords(employeeId, filter: filter);
  }

  // الحصول على السجلات غير المزامنة
  Future<List<Attendance>> getPendingSyncRecords(int employeeId) async {
    final filter = AttendanceFilter.pendingSync();
    return await getAttendanceRecords(employeeId, filter: filter);
  }

  // التحقق من حالة الحضور اليوم
  Future<Map<String, dynamic>> getTodayAttendanceStatus(int employeeId) async {
    try {
      final todayRecords = await getTodayRecords(employeeId);

      if (todayRecords.isEmpty) {
        return {
          'has_checked_in': false,
          'is_currently_active': false,
          'check_in_time': null,
          'check_out_time': null,
          'work_duration': '0:00',
          'status': 'لم يسجل حضور',
        };
      }

      final latestRecord = todayRecords.first;

      return {
        'has_checked_in': true,
        'is_currently_active': latestRecord.isActive,
        'check_in_time': latestRecord.getFormattedCheckIn(),
        'check_out_time': latestRecord.getFormattedCheckOut(),
        'work_duration': latestRecord.calculateDuration(),
        'status': latestRecord.isActive ? 'حضور نشط' : 'انتهى العمل',
        'is_local': latestRecord.isLocal,
        'is_synced': latestRecord.isSynced,
      };
    } catch (e) {
      throw DataNotFoundException('فشل في جلب حالة الحضور اليوم: $e');
    }
  }

  // تصدير البيانات كـ JSON
  Future<Map<String, dynamic>> exportAttendanceData(int employeeId) async {
    try {
      final records = await getAttendanceRecords(employeeId);
      final stats = await getAttendanceStats(employeeId);

      return {
        'employee_id': employeeId,
        'export_date': DateTime.now().toIso8601String(),
        'total_records': records.length,
        'records': records.map((record) => record.toJson()).toList(),
        'statistics': stats.toJson(),
      };
    } catch (e) {
      throw Exception('فشل في تصدير بيانات الحضور: $e');
    }
  }

  // استيراد البيانات من JSON
  Future<void> importAttendanceData(int employeeId, Map<String, dynamic> data) async {
    try {
      final recordsData = data['records'] as List;

      for (final recordData in recordsData) {
        final attendance = Attendance.fromJson(recordData);
        await saveLocalAttendance(attendance);
      }

      print('تم استيراد ${recordsData.length} سجل حضور');
    } catch (e) {
      throw Exception('فشل في استيراد بيانات الحضور: $e');
    }
  }

  // إحصائيات سريعة للواجهة الرئيسية
  Future<Map<String, dynamic>> getQuickStats(int employeeId) async {
    try {
      final todayStatus = await getTodayAttendanceStatus(employeeId);
      final thisWeekRecords = await getThisWeekRecords(employeeId);
      final pendingSync = await getPendingSyncRecords(employeeId);

      // حساب ساعات العمل هذا الأسبوع
      Duration weekWorkTime = Duration.zero;
      for (final record in thisWeekRecords) {
        if (record.checkOut != null) {
          weekWorkTime += record.checkOut!.difference(record.checkIn);
        }
      }

      return {
        'today_status': todayStatus,
        'week_work_hours': _formatDuration(weekWorkTime),
        'week_days_worked': thisWeekRecords.length,
        'pending_sync_count': pendingSync.length,
        'last_updated': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      return {
        'today_status': {'status': 'خطأ في التحميل'},
        'week_work_hours': '0:00',
        'week_days_worked': 0,
        'pending_sync_count': 0,
        'last_updated': DateTime.now().toIso8601String(),
        'error': e.toString(),
      };
    }
  }

  // تنسيق المدة الزمنية
  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes % 60;
    return '$hours:${minutes.toString().padLeft(2, '0')}';
  }

  // مسح جميع البيانات المحلية
  Future<void> clearAllLocalData(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // مسح سجلات الحضور
      await prefs.remove('${_attendanceKey}_$employeeId');

      // مسح الحضور الحالي
      await prefs.remove('${_currentAttendanceKey}_$employeeId');

      // مسح الإحصائيات
      await prefs.remove('${_statsKey}_$employeeId');

      print('تم مسح جميع بيانات الحضور المحلية للموظف $employeeId');
    } catch (e) {
      throw Exception('فشل في مسح البيانات المحلية: $e');
    }
  }

  // تهيئة المستودع
  void initialize(OdooService odooService) {
    // يمكن ربط OdooService هنا إذا لزم الأمر
  }
}