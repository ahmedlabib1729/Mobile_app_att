// services/offline_manager.dart - نسخة محدثة مع دعم طلبات الإجازة
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/cache_manager.dart';
import '../services/connectivity_service.dart';
import '../services/odoo_service.dart';
import '../services/leave_service.dart';
import '../models/leave_request.dart';
import '../models/leave_type.dart';

class OfflineManager {
  static final OfflineManager _instance = OfflineManager._internal();
  factory OfflineManager() => _instance;
  OfflineManager._internal();

  final ConnectivityService _connectivityService = ConnectivityService();
  OdooService? _odooService;
  LeaveService? _leaveService;

  bool get isOnline => _connectivityService.isOnline;

  // تهيئة الخدمة مع OdooService
  void initialize(OdooService odooService) {
    _odooService = odooService;
    _leaveService = LeaveService(odooService);
  }

  // معالجة تسجيل الحضور (مع دعم الوضع غير المتصل)
  Future<Map<String, dynamic>> handleCheckIn(int employeeId) async {
    if (isOnline && _odooService != null) {
      try {
        // محاولة التسجيل عبر الإنترنت
        final result = await _odooService!.checkIn(employeeId);

        if (result['success']) {
          // حفظ في الكاش عند النجاح
          await _cacheAttendanceAction(employeeId, 'check_in', DateTime.now());
          return result;
        } else {
          // في حالة فشل الطلب، حفظ الإجراء للمزامنة لاحقاً
          return await _saveOfflineCheckIn(employeeId);
        }
      } catch (e) {
        print('خطأ في تسجيل الحضور عبر الإنترنت: $e');
        // في حالة فشل الاتصال، حفظ الإجراء للمزامنة لاحقاً
        return await _saveOfflineCheckIn(employeeId);
      }
    } else {
      // في الوضع غير المتصل أو عدم توفر الخدمة
      return await _saveOfflineCheckIn(employeeId);
    }
  }

  // معالجة تسجيل الانصراف (مع دعم الوضع غير المتصل)
  Future<Map<String, dynamic>> handleCheckOut(int employeeId) async {
    if (isOnline && _odooService != null) {
      try {
        final result = await _odooService!.checkOut(employeeId);

        if (result['success']) {
          await _cacheAttendanceAction(employeeId, 'check_out', DateTime.now());
          return result;
        } else {
          return await _saveOfflineCheckOut(employeeId);
        }
      } catch (e) {
        print('خطأ في تسجيل الانصراف عبر الإنترنت: $e');
        return await _saveOfflineCheckOut(employeeId);
      }
    } else {
      return await _saveOfflineCheckOut(employeeId);
    }
  }

  // معالجة إنشاء طلب إجازة (مع دعم الوضع غير المتصل)
  Future<Map<String, dynamic>> handleCreateLeaveRequest({
    required int employeeId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    if (isOnline && _leaveService != null) {
      try {
        final result = await _leaveService!.createLeaveRequest(
          employeeId: employeeId,
          leaveTypeId: leaveTypeId,
          startDate: startDate,
          endDate: endDate,
          reason: reason,
        );

        if (result['success'] && result['offline'] != true) {
          // تم الإنشاء بنجاح عبر الإنترنت
          return result;
        } else {
          // حفظ للمزامنة لاحقاً
          return await _saveOfflineLeaveRequest(
            employeeId: employeeId,
            leaveTypeId: leaveTypeId,
            startDate: startDate,
            endDate: endDate,
            reason: reason,
          );
        }
      } catch (e) {
        print('خطأ في إنشاء طلب الإجازة عبر الإنترنت: $e');
        return await _saveOfflineLeaveRequest(
          employeeId: employeeId,
          leaveTypeId: leaveTypeId,
          startDate: startDate,
          endDate: endDate,
          reason: reason,
        );
      }
    } else {
      return await _saveOfflineLeaveRequest(
        employeeId: employeeId,
        leaveTypeId: leaveTypeId,
        startDate: startDate,
        endDate: endDate,
        reason: reason,
      );
    }
  }

  // معالجة إلغاء طلب إجازة (مع دعم الوضع غير المتصل)
  Future<Map<String, dynamic>> handleCancelLeaveRequest(int requestId) async {
    if (isOnline && _leaveService != null) {
      try {
        final result = await _leaveService!.cancelLeaveRequest(requestId);

        if (result['success'] && result['offline'] != true) {
          return result;
        } else {
          return await _saveOfflineCancelLeaveRequest(requestId);
        }
      } catch (e) {
        print('خطأ في إلغاء طلب الإجازة عبر الإنترنت: $e');
        return await _saveOfflineCancelLeaveRequest(requestId);
      }
    } else {
      return await _saveOfflineCancelLeaveRequest(requestId);
    }
  }

  // حفظ تسجيل حضور مؤجل
  Future<Map<String, dynamic>> _saveOfflineCheckIn(int employeeId) async {
    try {
      final timestamp = DateTime.now();

      final action = {
        'type': 'check_in',
        'employee_id': employeeId,
        'timestamp': timestamp.toIso8601String(),
        'local_id': DateTime.now().millisecondsSinceEpoch.toString(),
      };

      await CacheManager.saveOfflineAction(action);
      await _cacheAttendanceAction(employeeId, 'check_in', timestamp);

      return {
        'success': true,
        'offline': true,
        'message': 'تم تسجيل الحضور محلياً، سيتم المزامنة عند الاتصال',
        'timestamp': timestamp.toIso8601String(),
      };
    } catch (e) {
      print('خطأ في حفظ تسجيل الحضور المؤجل: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ تسجيل الحضور محلياً',
      };
    }
  }

  // حفظ تسجيل انصراف مؤجل
  Future<Map<String, dynamic>> _saveOfflineCheckOut(int employeeId) async {
    try {
      final timestamp = DateTime.now();

      final action = {
        'type': 'check_out',
        'employee_id': employeeId,
        'timestamp': timestamp.toIso8601String(),
        'local_id': DateTime.now().millisecondsSinceEpoch.toString(),
      };

      await CacheManager.saveOfflineAction(action);
      await _cacheAttendanceAction(employeeId, 'check_out', timestamp);

      return {
        'success': true,
        'offline': true,
        'message': 'تم تسجيل الانصراف محلياً، سيتم المزامنة عند الاتصال',
        'timestamp': timestamp.toIso8601String(),
      };
    } catch (e) {
      print('خطأ في حفظ تسجيل الانصراف المؤجل: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ تسجيل الانصراف محلياً',
      };
    }
  }

  // حفظ طلب إجازة مؤجل
  Future<Map<String, dynamic>> _saveOfflineLeaveRequest({
    required int employeeId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      final localId = DateTime.now().millisecondsSinceEpoch.toString();

      final action = {
        'type': 'create_leave_request',
        'employee_id': employeeId,
        'holiday_status_id': leaveTypeId,
        'date_from': startDate.toIso8601String(),
        'date_to': endDate.toIso8601String(),
        'name': reason,
        'local_id': localId,
        'timestamp': DateTime.now().toIso8601String(),
      };

      await CacheManager.saveOfflineAction(action);

      return {
        'success': true,
        'offline': true,
        'local_id': localId,
        'message': 'تم حفظ طلب الإجازة محلياً، سيتم إرساله عند الاتصال',
      };
    } catch (e) {
      print('خطأ في حفظ طلب الإجازة المؤجل: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ طلب الإجازة محلياً',
      };
    }
  }

  // حفظ إلغاء طلب إجازة مؤجل
  Future<Map<String, dynamic>> _saveOfflineCancelLeaveRequest(int requestId) async {
    try {
      final action = {
        'type': 'cancel_leave_request',
        'request_id': requestId,
        'timestamp': DateTime.now().toIso8601String(),
        'local_id': DateTime.now().millisecondsSinceEpoch.toString(),
      };

      await CacheManager.saveOfflineAction(action);

      return {
        'success': true,
        'offline': true,
        'message': 'تم حفظ إلغاء طلب الإجازة محلياً، سيتم تنفيذه عند الاتصال',
      };
    } catch (e) {
      print('خطأ في حفظ إلغاء طلب الإجازة المؤجل: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ إلغاء طلب الإجازة محلياً',
      };
    }
  }

  // حفظ إجراء الحضور في الكاش المحلي
  Future<void> _cacheAttendanceAction(int employeeId, String type, DateTime timestamp) async {
    try {
      final prefs = await SharedPreferences.getInstance();

      if (type == 'check_in') {
        await prefs.setBool('is_checked_in_$employeeId', true);
        await prefs.setString('check_in_time_$employeeId', timestamp.toIso8601String());
        await prefs.remove('check_out_time_$employeeId');
      } else if (type == 'check_out') {
        await prefs.setBool('is_checked_in_$employeeId', false);
        await prefs.setString('check_out_time_$employeeId', timestamp.toIso8601String());
        await prefs.remove('check_in_time_$employeeId');
      }

      print('تم حفظ إجراء $type في الكاش المحلي للموظف $employeeId');
    } catch (e) {
      print('خطأ في حفظ إجراء الحضور في الكاش: $e');
    }
  }

  // الحصول على حالة الحضور من الكاش المحلي
  Future<Map<String, dynamic>> getOfflineAttendanceStatus(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();

      final isCheckedIn = prefs.getBool('is_checked_in_$employeeId') ?? false;
      final checkInTimeString = prefs.getString('check_in_time_$employeeId');

      return {
        'is_checked_in': isCheckedIn,
        'check_in': checkInTimeString,
        'offline': true,
      };
    } catch (e) {
      print('خطأ في استرجاع حالة الحضور المحلية: $e');
      return {
        'is_checked_in': false,
        'check_in': null,
        'offline': true,
      };
    }
  }

  // مزامنة الإجراءات المؤجلة عند الاتصال
  Future<void> syncOfflineActions() async {
    if (!isOnline || _odooService == null) {
      print('لا يمكن المزامنة: غير متصل أو الخدمة غير متوفرة');
      return;
    }

    print('بدء مزامنة الإجراءات المؤجلة...');

    try {
      final offlineActions = await CacheManager.getOfflineActions();

      if (offlineActions.isEmpty) {
        print('لا توجد إجراءات مؤجلة للمزامنة');
        return;
      }

      print('عدد الإجراءات المؤجلة: ${offlineActions.length}');

      for (final action in offlineActions) {
        try {
          bool success = false;
          Map<String, dynamic>? result;

          switch (action['type']) {
            case 'check_in':
              result = await _odooService!.checkIn(action['employee_id']);
              success = result['success'] == true;
              break;

            case 'check_out':
              result = await _odooService!.checkOut(action['employee_id']);
              success = result['success'] == true;
              break;

            case 'create_leave_request':
              if (_leaveService != null) {
                result = await _leaveService!.createLeaveRequest(
                  employeeId: action['employee_id'],
                  leaveTypeId: action['holiday_status_id'],
                  startDate: DateTime.parse(action['date_from']),
                  endDate: DateTime.parse(action['date_to']),
                  reason: action['name'] ?? '',
                );
                success = result['success'] == true && result['offline'] != true;
              }
              break;

            case 'cancel_leave_request':
              if (_leaveService != null) {
                result = await _leaveService!.cancelLeaveRequest(action['request_id']);
                success = result['success'] == true && result['offline'] != true;
              }
              break;

            case 'update_leave_request':
              if (_leaveService != null) {
                result = await _leaveService!.updateLeaveRequest(
                  requestId: action['request_id'],
                  leaveTypeId: action['holiday_status_id'],
                  startDate: DateTime.parse(action['date_from']),
                  endDate: DateTime.parse(action['date_to']),
                  reason: action['name'] ?? '',
                );
                success = result['success'] == true && result['offline'] != true;
              }
              break;
          }

          if (success) {
            // إزالة الإجراء من قائمة الانتظار
            await CacheManager.removeOfflineAction(action['local_id'] ?? action['id']);
            print('تمت مزامنة إجراء: ${action['type']} للموظف ${action['employee_id'] ?? action['request_id']}');
          }

        } catch (e) {
          print('خطأ في مزامنة إجراء ${action['type']}: $e');
          // الإبقاء على الإجراء في قائمة الانتظار للمحاولة لاحقاً
        }
      }

      // تحديث وقت آخر مزامنة
      await CacheManager.updateLastSync();
      print('اكتملت مزامنة الإجراءات المؤجلة');

    } catch (e) {
      print('خطأ عام في مزامنة الإجراءات المؤجلة: $e');
      throw Exception('فشل في مزامنة البيانات المحفوظة محلياً');
    }
  }

  // الحصول على عدد الإجراءات المؤجلة
  Future<int> getPendingActionsCount() async {
    try {
      final actions = await CacheManager.getOfflineActions();
      return actions.length;
    } catch (e) {
      print('خطأ في حساب الإجراءات المؤجلة: $e');
      return 0;
    }
  }

  // الحصول على إحصائيات الإجراءات المؤجلة
  Future<Map<String, int>> getPendingActionsStats() async {
    try {
      final actions = await CacheManager.getOfflineActions();

      Map<String, int> stats = {
        'attendance': 0,
        'leave_requests': 0,
        'total': actions.length,
      };

      for (final action in actions) {
        switch (action['type']) {
          case 'check_in':
          case 'check_out':
            stats['attendance'] = (stats['attendance'] ?? 0) + 1;
            break;
          case 'create_leave_request':
          case 'update_leave_request':
          case 'cancel_leave_request':
            stats['leave_requests'] = (stats['leave_requests'] ?? 0) + 1;
            break;
        }
      }

      return stats;
    } catch (e) {
      print('خطأ في حساب إحصائيات الإجراءات المؤجلة: $e');
      return {'attendance': 0, 'leave_requests': 0, 'total': 0};
    }
  }

  // مزامنة إجراءات طلبات الإجازة فقط
  Future<void> syncLeaveRequests() async {
    if (!isOnline || _leaveService == null) {
      print('لا يمكن مزامنة طلبات الإجازة: غير متصل');
      return;
    }

    try {
      await _leaveService!.syncOfflineLeaveRequests();
      print('تمت مزامنة طلبات الإجازة بنجاح');
    } catch (e) {
      print('خطأ في مزامنة طلبات الإجازة: $e');
      throw e;
    }
  }

  // مزامنة إجراءات الحضور فقط
  Future<void> syncAttendanceActions() async {
    if (!isOnline || _odooService == null) {
      print('لا يمكن مزامنة إجراءات الحضور: غير متصل');
      return;
    }

    try {
      final offlineActions = await CacheManager.getOfflineActions();
      final attendanceActions = offlineActions.where((action) =>
      action['type'] == 'check_in' || action['type'] == 'check_out'
      ).toList();

      if (attendanceActions.isEmpty) {
        print('لا توجد إجراءات حضور مؤجلة للمزامنة');
        return;
      }

      print('مزامنة ${attendanceActions.length} إجراء حضور مؤجل...');

      for (final action in attendanceActions) {
        try {
          bool success = false;
          Map<String, dynamic>? result;

          switch (action['type']) {
            case 'check_in':
              result = await _odooService!.checkIn(action['employee_id']);
              success = result['success'] == true;
              break;

            case 'check_out':
              result = await _odooService!.checkOut(action['employee_id']);
              success = result['success'] == true;
              break;
          }

          if (success) {
            await CacheManager.removeOfflineAction(action['local_id'] ?? action['id']);
            print('تمت مزامنة إجراء حضور: ${action['type']} للموظف ${action['employee_id']}');
          }
        } catch (e) {
          print('خطأ في مزامنة إجراء حضور ${action['type']}: $e');
        }
      }

      print('اكتملت مزامنة إجراءات الحضور');
    } catch (e) {
      print('خطأ عام في مزامنة إجراءات الحضور: $e');
      throw e;
    }
  }

  // بدء دعم الوضع غير المتصل
  void startOfflineSupport() {
    _connectivityService.startMonitoring();

    // الاستماع لتغييرات حالة الاتصال
    _connectivityService.connectionStatusStream.listen((isOnline) {
      if (isOnline) {
        // بدء المزامنة عند الاتصال
        Future.delayed(Duration(seconds: 2), () {
          syncOfflineActions();
        });
      }
    });

    print('تم بدء دعم الوضع غير المتصل');
  }

  // إيقاف الخدمة
  void dispose() {
    _connectivityService.dispose();
    print('تم إيقاف OfflineManager');
  }
}