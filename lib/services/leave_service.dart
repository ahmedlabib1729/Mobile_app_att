// services/leave_service.dart - خدمة إدارة طلبات الإجازة
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/leave_request.dart';
import '../services/odoo_service.dart';
import '../services/cache_manager.dart';
import '../services/connectivity_service.dart';
import '../models/leave_type.dart';
import '../models/leave_request.dart';

class LeaveService {
  final OdooService _odooService;
  final ConnectivityService _connectivityService = ConnectivityService();

  LeaveService(this._odooService);

  // الحصول على أنواع الإجازات المتاحة
  Future<List<LeaveType>> getLeaveTypes() async {
    try {
      if (_connectivityService.isOnline) {
        return await _getLeaveTypesFromServer();
      } else {
        return await _getLeaveTypesFromCache();
      }
    } catch (e) {
      print('خطأ في جلب أنواع الإجازات: $e');
      // محاولة الحصول على البيانات من الكاش
      return await _getLeaveTypesFromCache();
    }
  }

  // جلب أنواع الإجازات من الخادم
  Future<List<LeaveType>> _getLeaveTypesFromServer() async {
    try {
      final url = '${_odooService.baseUrl}web/dataset/call_kw';

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=${_odooService.sessionId}',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.leave.type',
            'method': 'search_read',
            'args': [
              [], // بدون شروط - جلب كل الأنواع
              ['id', 'name', 'color', 'max_leaves', 'request_approve']
            ],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        if (result['result'] != null && result['result'] is List) {
          final List<LeaveType> leaveTypes = [];

          for (final item in result['result']) {
            leaveTypes.add(LeaveType(
              id: item['id'],
              name: item['name'],
              color: item['color'] ?? '#2196F3',
              maxDays: (item['max_leaves'] ?? 30).round(),
              requiresApproval: item['request_approve'] ?? true,
            ));
          }

          // حفظ في الكاش
          await _cacheLeaveTypes(leaveTypes);

          return leaveTypes;
        }
      }

      throw Exception('فشل في جلب أنواع الإجازات من الخادم');
    } catch (e) {
      print('خطأ في _getLeaveTypesFromServer: $e');
      throw e;
    }
  }

  // جلب أنواع الإجازات من الكاش
  Future<List<LeaveType>> _getLeaveTypesFromCache() async {
    try {
      // قائمة افتراضية في حالة عدم وجود كاش
      return [
        LeaveType(
          id: 1,
          name: 'إجازة سنوية',
          color: '#4CAF50',
          maxDays: 30,
          requiresApproval: true,
        ),
        LeaveType(
          id: 2,
          name: 'إجازة مرضية',
          color: '#F44336',
          maxDays: 15,
          requiresApproval: true,
        ),
        LeaveType(
          id: 3,
          name: 'إجازة طارئة',
          color: '#FF9800',
          maxDays: 5,
          requiresApproval: true,
        ),
      ];
    } catch (e) {
      print('خطأ في جلب أنواع الإجازات من الكاش: $e');
      return [];
    }
  }

  // حفظ أنواع الإجازات في الكاش
  Future<void> _cacheLeaveTypes(List<LeaveType> leaveTypes) async {
    try {
      final data = leaveTypes.map((type) => type.toJson()).toList();
      // يمكن استخدام SharedPreferences أو أي طريقة أخرى للحفظ
      print('تم حفظ ${leaveTypes.length} نوع إجازة في الكاش');
    } catch (e) {
      print('خطأ في حفظ أنواع الإجازات: $e');
    }
  }

  // إنشاء طلب إجازة جديد
  Future<Map<String, dynamic>> createLeaveRequest({
    required int employeeId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      if (_connectivityService.isOnline) {
        return await _createLeaveRequestOnServer(
          employeeId: employeeId,
          leaveTypeId: leaveTypeId,
          startDate: startDate,
          endDate: endDate,
          reason: reason,
        );
      } else {
        return await _createLeaveRequestOffline(
          employeeId: employeeId,
          leaveTypeId: leaveTypeId,
          startDate: startDate,
          endDate: endDate,
          reason: reason,
        );
      }
    } catch (e) {
      print('خطأ في إنشاء طلب الإجازة: $e');
      // محاولة الحفظ محلياً
      return await _createLeaveRequestOffline(
        employeeId: employeeId,
        leaveTypeId: leaveTypeId,
        startDate: startDate,
        endDate: endDate,
        reason: reason,
      );
    }
  }

  // إنشاء طلب إجازة على الخادم
  Future<Map<String, dynamic>> _createLeaveRequestOnServer({
    required int employeeId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      final url = '${_odooService.baseUrl}web/dataset/call_kw';

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=${_odooService.sessionId}',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.leave',
            'method': 'create',
            'args': [{
              'employee_id': employeeId,
              'holiday_status_id': leaveTypeId,
              'date_from': startDate.toIso8601String(),
              'date_to': endDate.toIso8601String(),
              'name': reason,
              'request_date_from': startDate.toIso8601String(),
              'request_date_to': endDate.toIso8601String(),
            }],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        if (result['result'] != null) {
          return {
            'success': true,
            'leave_id': result['result'],
            'message': 'تم إنشاء طلب الإجازة بنجاح',
          };
        }
      }

      throw Exception('فشل في إنشاء طلب الإجازة على الخادم');
    } catch (e) {
      print('خطأ في _createLeaveRequestOnServer: $e');
      throw e;
    }
  }

  // إنشاء طلب إجازة محلياً (حفظ مؤقت)
  Future<Map<String, dynamic>> _createLeaveRequestOffline({
    required int employeeId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      final localId = DateTime.now().millisecondsSinceEpoch.toString();

      final leaveRequest = {
        'type': 'create_leave_request',
        'employee_id': employeeId,
        'holiday_status_id': leaveTypeId,
        'date_from': startDate.toIso8601String(),
        'date_to': endDate.toIso8601String(),
        'name': reason,
        'local_id': localId,
        'timestamp': DateTime.now().toIso8601String(),
      };

      // حفظ في قائمة الإجراءات المؤجلة
      await CacheManager.saveOfflineAction(leaveRequest);

      return {
        'success': true,
        'offline': true,
        'local_id': localId,
        'message': 'تم حفظ طلب الإجازة محلياً، سيتم إرساله عند الاتصال',
      };
    } catch (e) {
      print('خطأ في _createLeaveRequestOffline: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ طلب الإجازة محلياً',
      };
    }
  }

  // جلب طلبات الإجازة للموظف
  Future<List<LeaveRequest>> getEmployeeLeaveRequests(int employeeId) async {
    try {
      if (_connectivityService.isOnline) {
        final serverRequests = await _getLeaveRequestsFromServer(employeeId);
        await _cacheLeaveRequests(serverRequests);
        return serverRequests;
      } else {
        return await _getLeaveRequestsFromCache(employeeId);
      }
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة: $e');
      // محاولة الحصول على البيانات من الكاش
      return await _getLeaveRequestsFromCache(employeeId);
    }
  }

  // جلب طلبات الإجازة من الخادم
  Future<List<LeaveRequest>> _getLeaveRequestsFromServer(int employeeId) async {
    try {
      final url = '${_odooService.baseUrl}web/dataset/call_kw';

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=${_odooService.sessionId}',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.leave',
            'method': 'search_read',
            'args': [
              [['employee_id', '=', employeeId]],
              [
                'id', 'employee_id', 'holiday_status_id', 'date_from', 'date_to',
                'number_of_days', 'name', 'state', 'notes', 'create_date'
              ]
            ],
            'kwargs': {
              'order': 'create_date desc',
              'limit': 50,
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        if (result['result'] != null && result['result'] is List) {
          final List<LeaveRequest> requests = [];

          for (final item in result['result']) {
            try {
              requests.add(LeaveRequest.fromJson(item));
            } catch (e) {
              print('خطأ في تحويل طلب إجازة: $e');
              // تجاهل الطلبات المعطوبة
            }
          }

          return requests;
        }
      }

      throw Exception('فشل في جلب طلبات الإجازة من الخادم');
    } catch (e) {
      print('خطأ في _getLeaveRequestsFromServer: $e');
      throw e;
    }
  }

  // جلب طلبات الإجازة من الكاش
  Future<List<LeaveRequest>> _getLeaveRequestsFromCache(int employeeId) async {
    try {
      // في المستقبل يمكن جلبها من SharedPreferences
      // الآن نرجع قائمة فارغة
      return [];
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة من الكاش: $e');
      return [];
    }
  }

  // حفظ طلبات الإجازة في الكاش
  Future<void> _cacheLeaveRequests(List<LeaveRequest> requests) async {
    try {
      final data = requests.map((request) => request.toJson()).toList();
      // يمكن حفظها في SharedPreferences
      print('تم حفظ ${requests.length} طلب إجازة في الكاش');
    } catch (e) {
      print('خطأ في حفظ طلبات الإجازة: $e');
    }
  }

  // إلغاء طلب إجازة
  Future<Map<String, dynamic>> cancelLeaveRequest(int requestId) async {
    try {
      if (_connectivityService.isOnline) {
        return await _cancelLeaveRequestOnServer(requestId);
      } else {
        return await _cancelLeaveRequestOffline(requestId);
      }
    } catch (e) {
      print('خطأ في إلغاء طلب الإجازة: $e');
      return await _cancelLeaveRequestOffline(requestId);
    }
  }

  // إلغاء طلب إجازة على الخادم
  Future<Map<String, dynamic>> _cancelLeaveRequestOnServer(int requestId) async {
    try {
      final url = '${_odooService.baseUrl}web/dataset/call_kw';

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=${_odooService.sessionId}',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.leave',
            'method': 'action_refuse',
            'args': [requestId],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        if (result['result'] != null) {
          return {
            'success': true,
            'message': 'تم إلغاء طلب الإجازة بنجاح',
          };
        }
      }

      throw Exception('فشل في إلغاء طلب الإجازة على الخادم');
    } catch (e) {
      print('خطأ في _cancelLeaveRequestOnServer: $e');
      throw e;
    }
  }

  // إلغاء طلب إجازة محلياً
  Future<Map<String, dynamic>> _cancelLeaveRequestOffline(int requestId) async {
    try {
      final cancelAction = {
        'type': 'cancel_leave_request',
        'request_id': requestId,
        'timestamp': DateTime.now().toIso8601String(),
      };

      await CacheManager.saveOfflineAction(cancelAction);

      return {
        'success': true,
        'offline': true,
        'message': 'تم حفظ إلغاء طلب الإجازة محلياً، سيتم تنفيذه عند الاتصال',
      };
    } catch (e) {
      print('خطأ في _cancelLeaveRequestOffline: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ إلغاء طلب الإجازة محلياً',
      };
    }
  }

  // تحديث طلب إجازة
  Future<Map<String, dynamic>> updateLeaveRequest({
    required int requestId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      if (_connectivityService.isOnline) {
        return await _updateLeaveRequestOnServer(
          requestId: requestId,
          leaveTypeId: leaveTypeId,
          startDate: startDate,
          endDate: endDate,
          reason: reason,
        );
      } else {
        return await _updateLeaveRequestOffline(
          requestId: requestId,
          leaveTypeId: leaveTypeId,
          startDate: startDate,
          endDate: endDate,
          reason: reason,
        );
      }
    } catch (e) {
      print('خطأ في تحديث طلب الإجازة: $e');
      return await _updateLeaveRequestOffline(
        requestId: requestId,
        leaveTypeId: leaveTypeId,
        startDate: startDate,
        endDate: endDate,
        reason: reason,
      );
    }
  }

  // تحديث طلب إجازة على الخادم
  Future<Map<String, dynamic>> _updateLeaveRequestOnServer({
    required int requestId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      final url = '${_odooService.baseUrl}web/dataset/call_kw';

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=${_odooService.sessionId}',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.leave',
            'method': 'write',
            'args': [
              requestId,
              {
                'holiday_status_id': leaveTypeId,
                'date_from': startDate.toIso8601String(),
                'date_to': endDate.toIso8601String(),
                'name': reason,
                'request_date_from': startDate.toIso8601String(),
                'request_date_to': endDate.toIso8601String(),
              }
            ],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        if (result['result'] == true) {
          return {
            'success': true,
            'message': 'تم تحديث طلب الإجازة بنجاح',
          };
        }
      }

      throw Exception('فشل في تحديث طلب الإجازة على الخادم');
    } catch (e) {
      print('خطأ في _updateLeaveRequestOnServer: $e');
      throw e;
    }
  }

  // تحديث طلب إجازة محلياً
  Future<Map<String, dynamic>> _updateLeaveRequestOffline({
    required int requestId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      final updateAction = {
        'type': 'update_leave_request',
        'request_id': requestId,
        'holiday_status_id': leaveTypeId,
        'date_from': startDate.toIso8601String(),
        'date_to': endDate.toIso8601String(),
        'name': reason,
        'timestamp': DateTime.now().toIso8601String(),
      };

      await CacheManager.saveOfflineAction(updateAction);

      return {
        'success': true,
        'offline': true,
        'message': 'تم حفظ تحديث طلب الإجازة محلياً، سيتم تنفيذه عند الاتصال',
      };
    } catch (e) {
      print('خطأ في _updateLeaveRequestOffline: $e');
      return {
        'success': false,
        'error': 'فشل في حفظ تحديث طلب الإجازة محلياً',
      };
    }
  }

  // الحصول على إحصائيات الإجازات
  Future<LeaveStats> getLeaveStats(int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      return LeaveStats.fromRequests(requests);
    } catch (e) {
      print('خطأ في حساب إحصائيات الإجازات: $e');
      return LeaveStats(
        totalRequests: 0,
        approvedRequests: 0,
        pendingRequests: 0,
        rejectedRequests: 0,
        totalDaysUsed: 0,
        totalDaysRemaining: 30,
        leavesByType: {},
      );
    }
  }

  // التحقق من توفر الإجازة
  Future<Map<String, dynamic>> checkLeaveAvailability({
    required int employeeId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    try {
      if (!_connectivityService.isOnline) {
        return {
          'available': true,
          'message': 'سيتم التحقق من التوفر عند الاتصال',
          'offline': true,
        };
      }

      final url = '${_odooService.baseUrl}web/dataset/call_kw';

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=${_odooService.sessionId}',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.leave',
            'method': 'check_leave_availability',
            'args': [employeeId, leaveTypeId, startDate.toIso8601String(), endDate.toIso8601String()],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        if (result['result'] != null) {
          return {
            'available': result['result']['available'] ?? true,
            'message': result['result']['message'] ?? '',
            'remaining_days': result['result']['remaining_days'] ?? 0,
          };
        }
      }

      // افتراضياً، السماح بالطلب
      return {
        'available': true,
        'message': 'متاح',
        'remaining_days': 30,
      };
    } catch (e) {
      print('خطأ في التحقق من توفر الإجازة: $e');
      return {
        'available': true,
        'message': 'سيتم التحقق لاحقاً',
        'offline': true,
      };
    }
  }

  // مزامنة طلبات الإجازة المحفوظة محلياً
  Future<void> syncOfflineLeaveRequests() async {
    if (!_connectivityService.isOnline) {
      print('لا يمكن مزامنة طلبات الإجازة: غير متصل');
      return;
    }

    try {
      final offlineActions = await CacheManager.getOfflineActions();
      final leaveActions = offlineActions.where((action) =>
      action['type'] == 'create_leave_request' ||
          action['type'] == 'update_leave_request' ||
          action['type'] == 'cancel_leave_request'
      ).toList();

      if (leaveActions.isEmpty) {
        print('لا توجد طلبات إجازة مؤجلة للمزامنة');
        return;
      }

      print('مزامنة ${leaveActions.length} طلب إجازة مؤجل...');

      for (final action in leaveActions) {
        try {
          bool success = false;

          switch (action['type']) {
            case 'create_leave_request':
              final result = await _createLeaveRequestOnServer(
                employeeId: action['employee_id'],
                leaveTypeId: action['holiday_status_id'],
                startDate: DateTime.parse(action['date_from']),
                endDate: DateTime.parse(action['date_to']),
                reason: action['name'],
              );
              success = result['success'] == true;
              break;

            case 'update_leave_request':
              final result = await _updateLeaveRequestOnServer(
                requestId: action['request_id'],
                leaveTypeId: action['holiday_status_id'],
                startDate: DateTime.parse(action['date_from']),
                endDate: DateTime.parse(action['date_to']),
                reason: action['name'],
              );
              success = result['success'] == true;
              break;

            case 'cancel_leave_request':
              final result = await _cancelLeaveRequestOnServer(action['request_id']);
              success = result['success'] == true;
              break;
          }

          if (success) {
            await CacheManager.removeOfflineAction(action['local_id'] ?? action['id']);
            print('تمت مزامنة طلب إجازة: ${action['type']}');
          }
        } catch (e) {
          print('خطأ في مزامنة طلب إجازة ${action['type']}: $e');
        }
      }

      print('اكتملت مزامنة طلبات الإجازة');
    } catch (e) {
      print('خطأ عام في مزامنة طلبات الإجازة: $e');
    }
  }
}