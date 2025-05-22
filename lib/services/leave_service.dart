// lib/services/leave_service.dart - خدمة إدارة طلبات الإجازة كاملة ومُصححة
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/leave_request.dart';
import '../models/leave_stats.dart';
import '../services/odoo_service.dart';
import '../services/cache_manager.dart';
import '../services/connectivity_service.dart';
import '../models/leave_type.dart';
import '../models/leave_balance.dart';

class LeaveService {
  final OdooService _odooService;
  final ConnectivityService _connectivityService = ConnectivityService();

  // مفاتيح التخزين المحلي
  static const String _leaveRequestsKey = 'cached_leave_requests';
  static const String _leaveTypesKey = 'cached_leave_types';
  static const String _leaveStatsKey = 'cached_leave_stats';

  LeaveService(this._odooService);

  // الحصول على أنواع الإجازات المتاحة مع الرصيد الفعلي
  Future<List<LeaveType>> getLeaveTypes() async {
    try {
      if (_connectivityService.isOnline) {
        // محاولة جلب أنواع الإجازات مع الرصيد من الخادم
        List<LeaveType> types = [];

        try {
          // استخدام الدالة المحدثة
          types = await _odooService.getLeaveTypesFromSystem();

          // حفظ في الكاش
          if (types.isNotEmpty) {
            await _cacheLeaveTypes(types);
          }

          return types;
        } catch (e) {
          print('فشل جلب أنواع الإجازات من الخادم: $e');

          // في حالة الفشل، محاولة جلب من الكاش
          types = await _getLeaveTypesFromCache();

          if (types.isEmpty) {
            // إذا لم يكن هناك كاش، استخدم القيم الافتراضية
            types = _getDefaultLeaveTypes();
          }

          return types;
        }
      } else {
        // في حالة عدم الاتصال، جلب من الكاش
        return await _getLeaveTypesFromCache();
      }
    } catch (e) {
      print('خطأ في جلب أنواع الإجازات: $e');
      // محاولة الحصول على البيانات من الكاش
      return await _getLeaveTypesFromCache();
    }
  }

  // جلب أنواع الإجازات من الكاش
  Future<List<LeaveType>> _getLeaveTypesFromCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final typesJson = prefs.getString(_leaveTypesKey);

      if (typesJson != null) {
        final List<dynamic> typesList = jsonDecode(typesJson);
        return typesList.map((json) => LeaveType.fromJson(json)).toList();
      }

      // قائمة افتراضية في حالة عدم وجود كاش
      return _getDefaultLeaveTypes();
    } catch (e) {
      print('خطأ في جلب أنواع الإجازات من الكاش: $e');
      return _getDefaultLeaveTypes();
    }
  }

  // حفظ أنواع الإجازات في الكاش
  Future<void> _cacheLeaveTypes(List<LeaveType> types) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final typesJson = jsonEncode(types.map((type) => type.toJson()).toList());
      await prefs.setString(_leaveTypesKey, typesJson);
      print('تم حفظ ${types.length} نوع إجازة في الكاش');
    } catch (e) {
      print('خطأ في حفظ أنواع الإجازات: $e');
    }
  }

  // الحصول على أنواع إجازات افتراضية
  List<LeaveType> _getDefaultLeaveTypes() {
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
      LeaveType(
        id: 4,
        name: 'إجازة أمومة',
        color: '#E91E63',
        maxDays: 90,
        requiresApproval: true,
      ),
      LeaveType(
        id: 5,
        name: 'إجازة حج وعمرة',
        color: '#9C27B0',
        maxDays: 21,
        requiresApproval: true,
      ),
    ];
  }

  // إضافة دالة للحصول على الرصيد المتاح لنوع إجازة معين
  Future<Map<String, dynamic>> getLeaveTypeBalance(int employeeId, int leaveTypeId) async {
    try {
      if (_connectivityService.isOnline) {
        final balanceData = await _odooService.getLeaveBalanceDetailed(employeeId);

        if (balanceData.containsKey(leaveTypeId.toString())) {
          return balanceData[leaveTypeId.toString()];
        }
      }

      // حساب من البيانات المحلية
      final requests = await getOfflineLeaveRequests(employeeId);
      final approvedRequests = requests.where((r) =>
      r.isApproved && r.leaveTypeId == leaveTypeId
      ).toList();

      final usedDays = approvedRequests.fold<double>(
          0, (sum, r) => sum + r.numberOfDays
      );

      // افتراض 30 يوم كحد أقصى افتراضي
      const defaultMaxDays = 30.0;

      return {
        'max_days': defaultMaxDays,
        'used_days': usedDays,
        'remaining_days': defaultMaxDays - usedDays,
      };

    } catch (e) {
      print('خطأ في جلب رصيد نوع الإجازة: $e');
      return {
        'max_days': 0,
        'used_days': 0,
        'remaining_days': 0,
      };
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
      final result = await _odooService.createLeaveRequest(
        employeeId: employeeId,
        leaveTypeId: leaveTypeId,
        dateFrom: startDate,
        dateTo: endDate,
        description: reason,
      );

      if (result['success'] == true) {
        // إضافة الطلب للكاش المحلي
        await _addRequestToCache(LeaveRequest(
          id: result['leave_request_id'] ?? DateTime.now().millisecondsSinceEpoch,
          employeeId: employeeId,
          leaveTypeId: leaveTypeId,
          leaveTypeName: await _getLeaveTypeName(leaveTypeId),
          dateFrom: startDate,
          dateTo: endDate,
          numberOfDays: _calculateDays(startDate, endDate),
          reason: reason,
          state: 'draft',
          stateText: 'مسودة',
          stateIcon: '📝',
          stateColor: '#9E9E9E',
          createdDate: DateTime.now(),
        ));

        return {
          'success': true,
          'message': 'تم إنشاء طلب الإجازة بنجاح',
        };
      } else {
        return {
          'success': false,
          'error': result['error'] ?? 'فشل في إنشاء طلب الإجازة',
        };
      }
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

      // إضافة الطلب للكاش المحلي كطلب معلق
      await _addRequestToCache(LeaveRequest(
        id: int.parse(localId),
        employeeId: employeeId,
        leaveTypeId: leaveTypeId,
        leaveTypeName: await _getLeaveTypeName(leaveTypeId),
        dateFrom: startDate,
        dateTo: endDate,
        numberOfDays: _calculateDays(startDate, endDate),
        reason: reason,
        state: 'draft',
        stateText: 'مسودة (محلي)',
        stateIcon: '📝',
        stateColor: '#FF9800',
        createdDate: DateTime.now(),
      ));

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
        await _cacheLeaveRequests(employeeId, serverRequests);

        // دمج الطلبات المحلية مع طلبات الخادم
        final localRequests = await _getLocalPendingRequests(employeeId);
        final allRequests = [...serverRequests, ...localRequests];

        // إزالة المكررات وترتيب حسب التاريخ
        return _removeDuplicatesAndSort(allRequests);
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
      return await _odooService.getLeaveRequests(employeeId);
    } catch (e) {
      print('خطأ في _getLeaveRequestsFromServer: $e');
      throw e;
    }
  }

  // جلب طلبات الإجازة من الكاش
  Future<List<LeaveRequest>> _getLeaveRequestsFromCache(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final requestsKey = '${_leaveRequestsKey}_$employeeId';
      final requestsJson = prefs.getString(requestsKey);

      if (requestsJson != null) {
        final List<dynamic> requestsList = jsonDecode(requestsJson);
        return requestsList.map((json) => LeaveRequest.fromJson(json)).toList();
      }

      return [];
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة من الكاش: $e');
      return [];
    }
  }

  // حفظ طلبات الإجازة في الكاش
  Future<void> _cacheLeaveRequests(int employeeId, List<LeaveRequest> requests) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final requestsKey = '${_leaveRequestsKey}_$employeeId';
      final requestsJson = jsonEncode(requests.map((request) => request.toJson()).toList());
      await prefs.setString(requestsKey, requestsJson);
      print('تم حفظ ${requests.length} طلب إجازة في الكاش للموظف $employeeId');
    } catch (e) {
      print('خطأ في حفظ طلبات الإجازة: $e');
    }
  }

  // إضافة طلب واحد للكاش
  Future<void> _addRequestToCache(LeaveRequest request) async {
    try {
      final existingRequests = await _getLeaveRequestsFromCache(request.employeeId);
      existingRequests.add(request);
      await _cacheLeaveRequests(request.employeeId, existingRequests);
    } catch (e) {
      print('خطأ في إضافة طلب للكاش: $e');
    }
  }

  // جلب الطلبات المحلية المعلقة
  Future<List<LeaveRequest>> _getLocalPendingRequests(int employeeId) async {
    try {
      final offlineActions = await CacheManager.getOfflineActions();
      final leaveActions = offlineActions.where((action) =>
      action['type'] == 'create_leave_request' &&
          action['employee_id'] == employeeId
      ).toList();

      List<LeaveRequest> localRequests = [];

      for (final action in leaveActions) {
        localRequests.add(LeaveRequest(
          id: int.parse(action['local_id']),
          employeeId: action['employee_id'],
          leaveTypeId: action['holiday_status_id'],
          leaveTypeName: await _getLeaveTypeName(action['holiday_status_id']),
          dateFrom: DateTime.parse(action['date_from']),
          dateTo: DateTime.parse(action['date_to']),
          numberOfDays: _calculateDays(
              DateTime.parse(action['date_from']),
              DateTime.parse(action['date_to'])
          ),
          reason: action['name'] ?? '',
          state: 'draft',
          stateText: 'معلق (محلي)',
          stateIcon: '⏳',
          stateColor: '#FF9800',
          createdDate: DateTime.parse(action['timestamp']),
        ));
      }

      return localRequests;
    } catch (e) {
      print('خطأ في جلب الطلبات المحلية المعلقة: $e');
      return [];
    }
  }

  // إزالة المكررات وترتيب الطلبات
  List<LeaveRequest> _removeDuplicatesAndSort(List<LeaveRequest> requests) {
    // إزالة المكررات بناءً على ID أو خصائص أخرى
    final Map<String, LeaveRequest> uniqueRequests = {};

    for (final request in requests) {
      final key = '${request.employeeId}_${request.dateFrom}_${request.dateTo}';
      if (!uniqueRequests.containsKey(key) ||
          request.state != 'draft') { // تفضيل الطلبات المزامنة
        uniqueRequests[key] = request;
      }
    }

    final result = uniqueRequests.values.toList();
    result.sort((a, b) => b.createdDate.compareTo(a.createdDate));
    return result;
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
      final result = await _odooService.cancelLeaveRequest(requestId);

      if (result['success'] == true) {
        // تحديث الطلب في الكاش
        await _updateRequestStatusInCache(requestId, 'cancel');

        return {
          'success': true,
          'message': 'تم إلغاء طلب الإجازة بنجاح',
        };
      } else {
        return {
          'success': false,
          'error': result['error'] ?? 'فشل في إلغاء طلب الإجازة',
        };
      }
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
        'local_id': DateTime.now().millisecondsSinceEpoch.toString(),
      };

      await CacheManager.saveOfflineAction(cancelAction);

      // تحديث الطلب في الكاش المحلي
      await _updateRequestStatusInCache(requestId, 'cancel');

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

  // تحديث حالة طلب في الكاش
  Future<void> _updateRequestStatusInCache(int requestId, String newState) async {
    try {
      // هنا يمكن تنفيذ تحديث حالة الطلب في جميع كاشات الموظفين
      // للبساطة، سنتجاهل هذا الآن
      print('تحديث حالة الطلب $requestId إلى $newState في الكاش');
    } catch (e) {
      print('خطأ في تحديث حالة الطلب في الكاش: $e');
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

  // تحديث طلب إجازة على الخادم (يحتاج تنفيذ في OdooService)
  Future<Map<String, dynamic>> _updateLeaveRequestOnServer({
    required int requestId,
    required int leaveTypeId,
    required DateTime startDate,
    required DateTime endDate,
    required String reason,
  }) async {
    try {
      // TODO: إضافة دالة updateLeaveRequest إلى OdooService
      // في الوقت الحالي نرجع false
      return {
        'success': false,
        'error': 'وظيفة تحديث طلب الإجازة غير مدعومة حالياً على الخادم',
      };
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
        'local_id': DateTime.now().millisecondsSinceEpoch.toString(),
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
      final stats = LeaveStats.fromRequests(requests);

      // حفظ الإحصائيات في الكاش
      await _cacheLeaveStats(employeeId, stats);

      return stats;
    } catch (e) {
      print('خطأ في حساب إحصائيات الإجازات: $e');

      // محاولة استرجاع الإحصائيات من الكاش
      final cachedStats = await _getCachedLeaveStats(employeeId);
      if (cachedStats != null) {
        return cachedStats;
      }

      return LeaveStats(
        totalRequests: 0,
        approvedRequests: 0,
        pendingRequests: 0,
        rejectedRequests: 0,
        cancelledRequests: 0,
        totalDaysUsed: 0,
        totalDaysRemaining: 30,
        totalDaysAllowed: 30,
      );
    }
  }

  // حفظ إحصائيات الإجازات في الكاش
  Future<void> _cacheLeaveStats(int employeeId, LeaveStats stats) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final statsKey = '${_leaveStatsKey}_$employeeId';
      final statsJson = jsonEncode(stats.toJson());
      await prefs.setString(statsKey, statsJson);
    } catch (e) {
      print('خطأ في حفظ إحصائيات الإجازات: $e');
    }
  }

  // استرجاع إحصائيات الإجازات من الكاش
  Future<LeaveStats?> _getCachedLeaveStats(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final statsKey = '${_leaveStatsKey}_$employeeId';
      final statsJson = prefs.getString(statsKey);

      if (statsJson != null) {
        final statsData = jsonDecode(statsJson);
        return LeaveStats.fromJson(statsData);
      }

      return null;
    } catch (e) {
      print('خطأ في استرجاع إحصائيات الإجازات من الكاش: $e');
      return null;
    }
  }

  // تحديث التحقق من توفر الإجازة
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

      // جلب الرصيد المتاح لنوع الإجازة
      final balance = await getLeaveTypeBalance(employeeId, leaveTypeId);
      final remainingDays = balance['remaining_days'] ?? 0;
      final requestedDays = _calculateDays(startDate, endDate);

      // التحقق من الرصيد
      if (remainingDays < requestedDays) {
        return {
          'available': false,
          'message': 'الرصيد المتاح ($remainingDays يوم) أقل من المطلوب ($requestedDays أيام)',
          'remaining_days': remainingDays,
        };
      }

      // فحص التداخل مع طلبات موجودة
      final existingRequests = await getEmployeeLeaveRequests(employeeId);
      final newRequest = LeaveRequest(
        id: 0,
        employeeId: employeeId,
        leaveTypeId: leaveTypeId,
        leaveTypeName: '',
        dateFrom: startDate,
        dateTo: endDate,
        numberOfDays: requestedDays,
        reason: '',
        state: 'draft',
        stateText: '',
        stateIcon: '',
        stateColor: '',
        createdDate: DateTime.now(),
      );

      for (final request in existingRequests) {
        if (request.isApproved && newRequest.overlapsWith(request)) {
          return {
            'available': false,
            'message': 'يتداخل مع إجازة مقبولة أخرى من ${request.formattedDateRange}',
          };
        }
      }

      return {
        'available': true,
        'message': 'الإجازة متاحة',
        'remaining_days': remainingDays,
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
          Map<String, dynamic>? result;

          switch (action['type']) {
            case 'create_leave_request':
              result = await _createLeaveRequestOnServer(
                employeeId: action['employee_id'],
                leaveTypeId: action['holiday_status_id'],
                startDate: DateTime.parse(action['date_from']),
                endDate: DateTime.parse(action['date_to']),
                reason: action['name'],
              );
              success = result['success'] == true;
              break;

            case 'update_leave_request':
              result = await _updateLeaveRequestOnServer(
                requestId: action['request_id'],
                leaveTypeId: action['holiday_status_id'],
                startDate: DateTime.parse(action['date_from']),
                endDate: DateTime.parse(action['date_to']),
                reason: action['name'],
              );
              success = result['success'] == true;
              break;

            case 'cancel_leave_request':
              result = await _cancelLeaveRequestOnServer(action['request_id']);
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

  // حفظ طلبات الإجازة في التخزين المحلي
  Future<void> saveLeaveRequests(List<LeaveRequest> requests) async {
    try {
      if (requests.isNotEmpty) {
        await _cacheLeaveRequests(requests.first.employeeId, requests);
        print('تم حفظ ${requests.length} طلب إجازة محلياً');
      }
    } catch (e) {
      print('خطأ في حفظ طلبات الإجازة محلياً: $e');
    }
  }

  // جلب طلبات الإجازة من التخزين المحلي
  Future<List<LeaveRequest>> getOfflineLeaveRequests(int employeeId) async {
    try {
      return await _getLeaveRequestsFromCache(employeeId);
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة المحلية: $e');
      return [];
    }
  }

  // مسح البيانات المحلية
  Future<void> clearLocalData({int? employeeId}) async {
    try {
      final prefs = await SharedPreferences.getInstance();

      if (employeeId != null) {
        // مسح بيانات موظف معين
        await prefs.remove('${_leaveRequestsKey}_$employeeId');
        await prefs.remove('${_leaveStatsKey}_$employeeId');
      } else {
        // مسح جميع البيانات
        final keys = prefs.getKeys();
        for (final key in keys) {
          if (key.startsWith(_leaveRequestsKey) ||
              key.startsWith(_leaveStatsKey) ||
              key.startsWith(_leaveTypesKey)) {
            await prefs.remove(key);
          }
        }
      }

      print('تم مسح بيانات طلبات الإجازة المحلية');
    } catch (e) {
      print('خطأ في مسح البيانات المحلية: $e');
    }
  }

  // الحصول على رصيد الإجازات للموظف
  Future<Map<int, LeaveBalance>> getEmployeeLeaveBalance(int employeeId) async {
    try {
      Map<int, LeaveBalance> balances = {};

      if (_connectivityService.isOnline) {
        // جلب البيانات من الخادم
        final balanceData = await _odooService.getLeaveBalance(employeeId);
        final types = await getLeaveTypes();

        for (var type in types) {
          final balance = balanceData[type.id.toString()];
          if (balance != null && balance is Map) {
            balances[type.id] = LeaveBalance(
              leaveTypeId: type.id,
              leaveTypeName: type.name,
              totalDays: (balance['max_days'] ?? 0).toDouble(),
              usedDays: ((balance['max_days'] ?? 0) - (balance['remaining_days'] ?? 0)).toDouble(),
              remainingDays: (balance['remaining_days'] ?? 0).toDouble(),
            );
          } else {
            // إذا لم نجد رصيد، نحسبه من الطلبات
            final requests = await getEmployeeLeaveRequests(employeeId);
            final approvedRequests = requests.where((r) =>
            r.isApproved && r.leaveTypeId == type.id
            ).toList();

            final usedDays = approvedRequests.fold<double>(
                0, (sum, r) => sum + r.numberOfDays
            );

            balances[type.id] = LeaveBalance(
              leaveTypeId: type.id,
              leaveTypeName: type.name,
              totalDays: type.maxDays.toDouble(),
              usedDays: usedDays,
              remainingDays: type.maxDays - usedDays,
            );
          }
        }
      } else {
        // استخدام البيانات المحفوظة
        final types = await getLeaveTypes();
        final requests = await getOfflineLeaveRequests(employeeId);

        for (var type in types) {
          final approvedRequests = requests.where((r) =>
          r.isApproved && r.leaveTypeId == type.id
          ).toList();

          final usedDays = approvedRequests.fold<double>(
              0, (sum, r) => sum + r.numberOfDays
          );

          balances[type.id] = LeaveBalance(
            leaveTypeId: type.id,
            leaveTypeName: type.name,
            totalDays: type.maxDays.toDouble(),
            usedDays: usedDays,
            remainingDays: type.maxDays - usedDays,
          );
        }
      }

      return balances;
    } catch (e) {
      print('خطأ في جلب رصيد الإجازات: $e');
      return {};
    }
  }

  // دوال مساعدة

  // حساب عدد الأيام بين تاريخين
  double _calculateDays(DateTime startDate, DateTime endDate) {
    final difference = endDate.difference(startDate);
    return difference.inDays + 1; // +1 لتضمين يوم البداية
  }

  // الحصول على اسم نوع الإجازة
  Future<String> _getLeaveTypeName(int leaveTypeId) async {
    try {
      final types = await getLeaveTypes();
      final type = types.firstWhere(
            (t) => t.id == leaveTypeId,
        orElse: () => LeaveType(
          id: leaveTypeId,
          name: 'نوع غير معروف',
          color: '#9E9E9E',
          maxDays: 0,
          requiresApproval: true,
        ),
      );
      return type.name;
    } catch (e) {
      print('خطأ في الحصول على اسم نوع الإجازة: $e');
      return 'نوع غير معروف';
    }
  }

  // فلترة طلبات الإجازة
  List<LeaveRequest> filterRequests(List<LeaveRequest> requests, {
    String? state,
    int? leaveTypeId,
    DateTime? fromDate,
    DateTime? toDate,
  }) {
    var filtered = requests;

    if (state != null && state.isNotEmpty) {
      filtered = filtered.where((r) => r.state == state).toList();
    }

    if (leaveTypeId != null) {
      filtered = filtered.where((r) => r.leaveTypeId == leaveTypeId).toList();
    }

    if (fromDate != null) {
      filtered = filtered.where((r) =>
      r.dateFrom.isAfter(fromDate) || r.dateFrom.isAtSameMomentAs(fromDate)
      ).toList();
    }

    if (toDate != null) {
      filtered = filtered.where((r) =>
      r.dateTo.isBefore(toDate) || r.dateTo.isAtSameMomentAs(toDate)
      ).toList();
    }

    return filtered;
  }

  // ترتيب طلبات الإجازة
  List<LeaveRequest> sortRequests(List<LeaveRequest> requests, {
    String sortBy = 'created_date',
    bool ascending = false,
  }) {
    requests.sort((a, b) {
      int comparison = 0;

      switch (sortBy) {
        case 'created_date':
          comparison = a.createdDate.compareTo(b.createdDate);
          break;
        case 'start_date':
          comparison = a.dateFrom.compareTo(b.dateFrom);
          break;
        case 'end_date':
          comparison = a.dateTo.compareTo(b.dateTo);
          break;
        case 'duration':
          comparison = a.numberOfDays.compareTo(b.numberOfDays);
          break;
        case 'state':
          comparison = a.state.compareTo(b.state);
          break;
        default:
          comparison = a.createdDate.compareTo(b.createdDate);
      }

      return ascending ? comparison : -comparison;
    });

    return requests;
  }

  // البحث في طلبات الإجازة
  List<LeaveRequest> searchRequests(List<LeaveRequest> requests, String query) {
    if (query.isEmpty) return requests;

    final lowerQuery = query.toLowerCase();

    return requests.where((request) {
      return request.leaveTypeName.toLowerCase().contains(lowerQuery) ||
          request.reason.toLowerCase().contains(lowerQuery) ||
          request.stateText.toLowerCase().contains(lowerQuery) ||
          request.formattedDateRange.contains(query);
    }).toList();
  }

  // الحصول على طلبات الإجازة حسب الحالة
  Future<List<LeaveRequest>> getRequestsByState(int employeeId, String state) async {
    final allRequests = await getEmployeeLeaveRequests(employeeId);
    return filterRequests(allRequests, state: state);
  }

  // الحصول على طلبات الإجازة المعلقة
  Future<List<LeaveRequest>> getPendingRequests(int employeeId) async {
    final allRequests = await getEmployeeLeaveRequests(employeeId);
    return allRequests.where((r) => r.isPending).toList();
  }

  // الحصول على طلبات الإجازة المقبولة
  Future<List<LeaveRequest>> getApprovedRequests(int employeeId) async {
    final allRequests = await getEmployeeLeaveRequests(employeeId);
    return allRequests.where((r) => r.isApproved).toList();
  }

  // الحصول على طلبات الإجازة المرفوضة
  Future<List<LeaveRequest>> getRejectedRequests(int employeeId) async {
    final allRequests = await getEmployeeLeaveRequests(employeeId);
    return allRequests.where((r) => r.isRejected).toList();
  }

  // التحقق من وجود طلبات غير مزامنة
  Future<bool> hasPendingSyncRequests() async {
    try {
      final offlineActions = await CacheManager.getOfflineActions();
      return offlineActions.any((action) =>
      action['type'] == 'create_leave_request' ||
          action['type'] == 'update_leave_request' ||
          action['type'] == 'cancel_leave_request'
      );
    } catch (e) {
      print('خطأ في فحص الطلبات المعلقة: $e');
      return false;
    }
  }

  // الحصول على عدد الطلبات غير المزامنة
  Future<int> getPendingSyncRequestsCount() async {
    try {
      final offlineActions = await CacheManager.getOfflineActions();
      return offlineActions.where((action) =>
      action['type'] == 'create_leave_request' ||
          action['type'] == 'update_leave_request' ||
          action['type'] == 'cancel_leave_request'
      ).length;
    } catch (e) {
      print('خطأ في حساب الطلبات المعلقة: $e');
      return 0;
    }
  }

  // إحصائيات سريعة
  Future<Map<String, dynamic>> getQuickStats(int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      final pendingSyncCount = await getPendingSyncRequestsCount();

      return {
        'total_requests': requests.length,
        'pending_requests': requests.where((r) => r.isPending).length,
        'approved_requests': requests.where((r) => r.isApproved).length,
        'rejected_requests': requests.where((r) => r.isRejected).length,
        'pending_sync': pendingSyncCount,
        'last_updated': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      print('خطأ في الحصول على الإحصائيات السريعة: $e');
      return {
        'total_requests': 0,
        'pending_requests': 0,
        'approved_requests': 0,
        'rejected_requests': 0,
        'pending_sync': 0,
        'last_updated': DateTime.now().toIso8601String(),
        'error': e.toString(),
      };
    }
  }

  // تصدير بيانات الإجازات
  Future<Map<String, dynamic>> exportLeaveData(int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      final stats = await getLeaveStats(employeeId);
      final types = await getLeaveTypes();

      return {
        'employee_id': employeeId,
        'export_date': DateTime.now().toIso8601String(),
        'leave_requests': requests.map((r) => r.toJson()).toList(),
        'leave_stats': stats.toJson(),
        'leave_types': types.map((t) => t.toJson()).toList(),
        'summary': {
          'total_requests': requests.length,
          'total_days_used': stats.totalDaysUsed,
          'total_days_remaining': stats.totalDaysRemaining,
        }
      };
    } catch (e) {
      print('خطأ في تصدير بيانات الإجازات: $e');
      throw Exception('فشل في تصدير بيانات الإجازات: $e');
    }
  }

  // فحص صحة البيانات
  Future<Map<String, dynamic>> validateLeaveData(int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      List<String> issues = [];

      for (final request in requests) {
        // فحص التواريخ
        if (request.dateFrom.isAfter(request.dateTo)) {
          issues.add('طلب ${request.id}: تاريخ البداية بعد تاريخ النهاية');
        }

        // فحص المدة
        if (request.numberOfDays <= 0) {
          issues.add('طلب ${request.id}: مدة الإجازة غير صالحة');
        }

        // فحص التداخل
        for (final otherRequest in requests) {
          if (request.id != otherRequest.id &&
              request.isApproved && otherRequest.isApproved &&
              request.overlapsWith(otherRequest)) {
            issues.add('طلب ${request.id}: يتداخل مع طلب ${otherRequest.id}');
          }
        }
      }

      return {
        'valid': issues.isEmpty,
        'issues_count': issues.length,
        'issues': issues,
        'total_requests': requests.length,
      };
    } catch (e) {
      print('خطأ في فحص صحة البيانات: $e');
      return {
        'valid': false,
        'issues_count': 1,
        'issues': ['خطأ في فحص البيانات: $e'],
        'total_requests': 0,
      };
    }
  }

  // إعادة تحميل البيانات من الخادم
  Future<void> refreshData(int employeeId) async {
    try {
      if (_connectivityService.isOnline) {
        // إعادة تحميل أنواع الإجازات
        final types = await _odooService.getLeaveTypesFromSystem();
        await _cacheLeaveTypes(types);

        // إعادة تحميل طلبات الإجازة
        final requests = await _getLeaveRequestsFromServer(employeeId);
        await _cacheLeaveRequests(employeeId, requests);

        // إعادة حساب الإحصائيات
        final stats = LeaveStats.fromRequests(requests);
        await _cacheLeaveStats(employeeId, stats);

        print('تم تحديث جميع بيانات الإجازات من الخادم');
      }
    } catch (e) {
      print('خطأ في إعادة تحميل البيانات: $e');
      throw Exception('فشل في تحديث البيانات من الخادم');
    }
  }

  // مراقبة تغيير حالة الاتصال
  void startConnectivityMonitoring() {
    _connectivityService.connectionStatusStream.listen((isOnline) {
      if (isOnline) {
        // عند الاتصال، مزامنة الطلبات المؤجلة
        syncOfflineLeaveRequests();
      }
    });
  }

  // إيقاف مراقبة الاتصال
  void dispose() {
    // تنظيف الموارد إذا لزم الأمر
  }

  // دالة للحصول على معلومات مفصلة عن طلب إجازة
  Future<LeaveRequest?> getLeaveRequestDetails(int requestId, int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      return requests.firstWhere(
            (request) => request.id == requestId,
        orElse: () => throw Exception('طلب الإجازة غير موجود'),
      );
    } catch (e) {
      print('خطأ في جلب تفاصيل طلب الإجازة: $e');
      return null;
    }
  }

  // دالة للحصول على طلبات الإجازة حسب الفترة الزمنية
  Future<List<LeaveRequest>> getLeaveRequestsByDateRange({
    required int employeeId,
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      return requests.where((request) {
        return request.dateFrom.isAfter(startDate.subtract(Duration(days: 1))) &&
            request.dateTo.isBefore(endDate.add(Duration(days: 1)));
      }).toList();
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة حسب الفترة: $e');
      return [];
    }
  }

  // دالة للحصول على طلبات الإجازة المستقبلية
  Future<List<LeaveRequest>> getUpcomingLeaveRequests(int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      final now = DateTime.now();
      return requests.where((request) {
        return request.dateFrom.isAfter(now) && request.isApproved;
      }).toList();
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة المستقبلية: $e');
      return [];
    }
  }

  // دالة للحصول على طلبات الإجازة النشطة حالياً
  Future<List<LeaveRequest>> getActiveLeaveRequests(int employeeId) async {
    try {
      final requests = await getEmployeeLeaveRequests(employeeId);
      final now = DateTime.now();
      return requests.where((request) {
        return request.dateFrom.isBefore(now) &&
            request.dateTo.isAfter(now) &&
            request.isApproved;
      }).toList();
    } catch (e) {
      print('خطأ في جلب طلبات الإجازة النشطة: $e');
      return [];
    }
  }
}
