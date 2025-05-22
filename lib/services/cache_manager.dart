// services/cache_manager.dart - نسخة مبسطة
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/employee.dart';

class CacheManager {
  static const String _employeeKey = 'cached_employee';
  static const String _attendanceHistoryKey = 'cached_attendance_history';
  static const String _offlineActionsKey = 'offline_actions';

  // حفظ بيانات الموظف
  static Future<void> cacheEmployee(Employee employee) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final employeeJson = jsonEncode({
        'id': employee.id,
        'name': employee.name,
        'job_title': employee.jobTitle,
        'department': employee.department,
        'work_email': employee.workEmail,
        'work_phone': employee.workPhone,
        'mobile_phone': employee.mobilePhone,
        'cached_at': DateTime.now().millisecondsSinceEpoch,
      });

      await prefs.setString(_employeeKey, employeeJson);
    } catch (e) {
      print('خطأ في حفظ بيانات الموظف: $e');
    }
  }

  // استرجاع بيانات الموظف
  static Future<Employee?> getCachedEmployee() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final employeeJson = prefs.getString(_employeeKey);

      if (employeeJson == null) return null;

      final data = jsonDecode(employeeJson);

      return Employee(
        id: data['id'],
        name: data['name'],
        jobTitle: data['job_title'] ?? '',
        department: data['department'] ?? '',
        workEmail: data['work_email'] ?? '',
        workPhone: data['work_phone'] ?? '',
        mobilePhone: data['mobile_phone'] ?? '',
      );
    } catch (e) {
      print('خطأ في استرجاع بيانات الموظف: $e');
      return null;
    }
  }

  // حفظ سجل الحضور
  static Future<void> cacheAttendanceHistory(List<Map<String, dynamic>> history) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final historyJson = jsonEncode({
        'history': history,
        'cached_at': DateTime.now().millisecondsSinceEpoch,
      });

      await prefs.setString(_attendanceHistoryKey, historyJson);
    } catch (e) {
      print('خطأ في حفظ سجل الحضور: $e');
    }
  }

  // استرجاع سجل الحضور
  static Future<List<Map<String, dynamic>>?> getCachedAttendanceHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final historyJson = prefs.getString(_attendanceHistoryKey);

      if (historyJson == null) return null;

      final data = jsonDecode(historyJson);
      return List<Map<String, dynamic>>.from(data['history']);
    } catch (e) {
      print('خطأ في استرجاع سجل الحضور: $e');
      return null;
    }
  }

  // حفظ إجراء مؤجل
  static Future<void> saveOfflineAction(Map<String, dynamic> action) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final existingActions = prefs.getStringList(_offlineActionsKey) ?? [];

      final actionJson = jsonEncode({
        ...action,
        'timestamp': DateTime.now().millisecondsSinceEpoch,
        'id': DateTime.now().millisecondsSinceEpoch.toString(),
      });

      existingActions.add(actionJson);
      await prefs.setStringList(_offlineActionsKey, existingActions);
    } catch (e) {
      print('خطأ في حفظ الإجراء المؤجل: $e');
    }
  }

  // استرجاع الإجراءات المؤجلة
  static Future<List<Map<String, dynamic>>> getOfflineActions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final actionsJson = prefs.getStringList(_offlineActionsKey) ?? [];

      return actionsJson.map((actionJson) {
        return Map<String, dynamic>.from(jsonDecode(actionJson));
      }).toList();
    } catch (e) {
      print('خطأ في استرجاع الإجراءات المؤجلة: $e');
      return [];
    }
  }

  // مسح إجراء مؤجل
  static Future<void> removeOfflineAction(String actionId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final actionsJson = prefs.getStringList(_offlineActionsKey) ?? [];

      actionsJson.removeWhere((actionJson) {
        final action = jsonDecode(actionJson);
        return action['id'] == actionId;
      });

      await prefs.setStringList(_offlineActionsKey, actionsJson);
    } catch (e) {
      print('خطأ في مسح الإجراء المؤجل: $e');
    }
  }

  // تحديث وقت آخر مزامنة
  static Future<void> updateLastSync() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt('last_sync', DateTime.now().millisecondsSinceEpoch);
    } catch (e) {
      print('خطأ في تحديث وقت المزامنة: $e');
    }
  }

  // الحصول على وقت آخر مزامنة
  static Future<DateTime?> getLastSync() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final timestamp = prefs.getInt('last_sync');

      if (timestamp == null) return null;
      return DateTime.fromMillisecondsSinceEpoch(timestamp);
    } catch (e) {
      return null;
    }
  }

  // التحقق من الحاجة للمزامنة
  static Future<bool> needsSync() async {
    final lastSync = await getLastSync();
    if (lastSync == null) return true;

    return DateTime.now().difference(lastSync).inMinutes > 15;
  }

  // مسح جميع البيانات
  static Future<void> clearCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_employeeKey);
      await prefs.remove(_attendanceHistoryKey);
      await prefs.remove(_offlineActionsKey);
    } catch (e) {
      print('خطأ في مسح البيانات: $e');
    }
  }
}