import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import '../models/employee.dart';
import '../models/leave_type.dart';
import '../models/leave_request.dart';

class OdooService {
  // البيانات الأساسية للاتصال بـ Odoo
  late String baseUrl;
  final String database;

  // بيانات جلسة الاتصال
  String? sessionId;
  int? uid;

  // بيانات المستخدم المشترك (Service User)
  final String serviceUsername = 'admin';
  final String servicePassword = 'admin';

  // بيانات الموظف الحالي
  int? employeeId;
  Employee? currentEmployee;

  OdooService({
    required String url,
    required this.database,
  }) {
    // تأكد من أن baseUrl ينتهي بـ / فقط مرة واحدة
    if (url.endsWith('/')) {
      this.baseUrl = url;
    } else {
      this.baseUrl = url + '/';
    }
    print("تم تهيئة OdooService مع baseUrl: ${this.baseUrl}");
  }

  // اختبار اتصال API
  Future<bool> testApiConnection() async {
    try {
      final testUrl = '${baseUrl}api/mobile/version';
      print("اختبار اتصال API على $testUrl");

      final response = await http.get(
        Uri.parse(testUrl),
      ).timeout(const Duration(seconds: 10));

      print("استجابة اختبار API: ${response.statusCode}");
      print("محتوى استجابة اختبار API: ${response.body}");

      return response.statusCode == 200;
    } catch (e) {
      print('خطأ في اختبار اتصال API: $e');
      return false;
    }
  }

  // اختبار بسيط للاتصال بالخادم
  Future<bool> testServerConnection() async {
    try {
      final response = await http.get(Uri.parse(baseUrl))
          .timeout(const Duration(seconds: 10));
      print("استجابة اختبار الخادم: ${response.statusCode}");
      return response.statusCode == 200;
    } catch (e) {
      print("خطأ في الاتصال بالخادم: $e");
      return false;
    }
  }

  // تسجيل الدخول باستخدام المستخدم المشترك
  Future<bool> loginWithService() async {
    try {
      print("محاولة تسجيل الدخول باستخدام مستخدم الخدمة: $serviceUsername إلى $baseUrl");

      final loginUrl = '${baseUrl}web/session/authenticate';
      print("إرسال طلب تسجيل الدخول إلى: $loginUrl");

      final requestBody = {
        'jsonrpc': '2.0',
        'params': {
          'db': database,
          'login': serviceUsername,
          'password': servicePassword,
        }
      };

      print("بيانات الطلب: ${jsonEncode(requestBody)}");

      final response = await http.post(
        Uri.parse(loginUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      ).timeout(const Duration(seconds: 15));

      print("استجابة تسجيل دخول الخدمة: ${response.statusCode}");

      if (response.statusCode != 200) {
        print("فشل تسجيل دخول الخدمة - رمز الاستجابة: ${response.statusCode}");
        return false;
      }

      final result = jsonDecode(response.body);

      // طباعة جزء من النتيجة فقط (قد تكون كبيرة)
      final resultString = result.toString();
      print("نتيجة تسجيل دخول الخدمة: ${resultString.length > 300 ? resultString.substring(0, 300) + '...' : resultString}");

      if (result['result'] != null && result['result']['uid'] != null) {
        uid = result['result']['uid'];
        print("تم تسجيل الدخول بنجاح، معرف المستخدم: $uid");

        // استخراج معرّف الجلسة من الكوكيز
        String? cookies = response.headers['set-cookie'];
        print("ترويسة Set-Cookie: $cookies");

        if (cookies != null) {
          final sessionRegex = RegExp(r'session_id=([^;]+)');
          final match = sessionRegex.firstMatch(cookies);
          if (match != null) {
            sessionId = match.group(1);
            print("تم استخراج معرف الجلسة: $sessionId");

            // حفظ البيانات للجلسات المستقبلية
            final prefs = await SharedPreferences.getInstance();
            await prefs.setString('session_id', sessionId!);
            await prefs.setInt('uid', uid!);

            return true;
          }
        }
      }

      print("فشل تسجيل الدخول باستخدام مستخدم الخدمة");
      return false;
    } catch (e) {
      print('خطأ في loginWithService: $e');
      return false;
    }
  }

  // استعادة البيانات المحفوظة
  Future<bool> restoreSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      sessionId = prefs.getString('session_id');
      uid = prefs.getInt('uid');
      employeeId = prefs.getInt('employee_id');

      print("تمت استعادة الجلسة - معرف الجلسة: $sessionId، معرف المستخدم: $uid، معرف الموظف: $employeeId");

      return sessionId != null && uid != null;
    } catch (e) {
      print('خطأ في restoreSession: $e');
      return false;
    }
  }

  // مصادقة الموظف باستخدام الـ mobile_username و mobile_pin
  Future<Employee?> authenticateEmployee(String username, String pin) async {
    try {
      print('محاولة المصادقة على المستخدم: $username');

      // تسجيل دخول المستخدم المشترك أولاً
      bool loginSuccess = await loginWithService();
      if (!loginSuccess) {
        print('فشل تسجيل دخول المستخدم المشترك');
        return null;
      }

      print('تم تسجيل دخول المستخدم المشترك بنجاح، جاري المصادقة على الموظف...');

      // استخدام وظيفة verify_employee_credentials المخصصة
      final url = '${baseUrl}web/dataset/call_kw';
      final requestBody = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
          'model': 'hr.employee',
          'method': 'verify_employee_credentials',
          'args': [username, pin],
          'kwargs': {},
        },
        'id': DateTime.now().millisecondsSinceEpoch
      };

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: jsonEncode(requestBody),
      ).timeout(const Duration(seconds: 15));

      print('استجابة التحقق من بيانات الموظف: ${response.statusCode}');
      final result = jsonDecode(response.body);
      print('محتوى استجابة التحقق: $result');

      if (result.containsKey('result') &&
          result['result'] != null &&
          result['result'].containsKey('success') &&
          result['result']['success'] == true) {

        // تم التحقق من الموظف بنجاح
        final employeeData = result['result']['employee'];
        print('تم التحقق من الموظف بنجاح: ${employeeData['name']}');

        // حفظ معرف الموظف
        employeeId = employeeData['id'];
        final prefs = await SharedPreferences.getInstance();
        await prefs.setInt('employee_id', employeeId!);

        // إنشاء كائن الموظف باستخدام البيانات المسترجعة
        currentEmployee = Employee(
          id: employeeData['id'],
          name: employeeData['name'],
          jobTitle: employeeData['job_title'] == false ? '' : employeeData['job_title'].toString(),
          department: employeeData['department'] == false ? '' : employeeData['department'].toString(),
          workEmail: employeeData['work_email'] == false ? '' : employeeData['work_email'].toString(),
          workPhone: employeeData['work_phone'] == false ? '' : employeeData['work_phone'].toString(),
          mobilePhone: '', // لا يوجد في الاستجابة
        );

        print('تمت المصادقة على الموظف بنجاح: ${currentEmployee!.name}');
        return currentEmployee;
      } else {
        // فشل التحقق
        String errorMsg = 'فشل التحقق من بيانات الموظف';
        if (result.containsKey('result') &&
            result['result'] != null &&
            result['result'].containsKey('error')) {
          errorMsg = result['result']['error'];
        }
        print('خطأ في المصادقة: $errorMsg');
        throw Exception(errorMsg);
      }
    } catch (e) {
      print('خطأ في authenticateEmployee: $e');
      throw Exception('لم نتمكن من المصادقة. يرجى التحقق من اتصال الشبكة وبيانات الاعتماد.');
    }
  }

  // الحصول على بيانات الموظف الحالي
  Future<Employee?> getCurrentEmployee() async {
    // إذا كانت بيانات الموظف موجودة بالفعل
    if (currentEmployee != null) {
      return currentEmployee;
    }

    // إذا كان لدينا فقط معرف الموظف
    if (employeeId != null) {
      try {
        print('جلب بيانات الموظف للمعرف: $employeeId');

        // التأكد من أن لدينا جلسة نشطة
        if (sessionId == null || uid == null) {
          bool loginSuccess = await loginWithService();
          if (!loginSuccess) {
            print('فشل تسجيل الدخول باستخدام مستخدم الخدمة');
            return null;
          }
        }

        final url = '${baseUrl}web/dataset/call_kw';
        final response = await http.post(
          Uri.parse(url),
          headers: {
            'Content-Type': 'application/json',
            'Cookie': 'session_id=$sessionId',
          },
          body: jsonEncode({
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
              'model': 'hr.employee',
              'method': 'search_read',
              'args': [
                [['id', '=', employeeId]],
                ['id', 'name', 'job_title', 'department_id', 'work_email', 'work_phone', 'mobile_phone']
              ],
              'kwargs': {
                'context': {},
              },
            },
            'id': DateTime.now().millisecondsSinceEpoch
          }),
        ).timeout(const Duration(seconds: 15));

        final result = jsonDecode(response.body);
        print('استجابة بيانات الموظف: $result');

        if (result['result'] != null && result['result'].isNotEmpty) {
          final employeeData = result['result'][0];

          currentEmployee = Employee(
            id: employeeData['id'],
            name: employeeData['name'],
            jobTitle: employeeData['job_title'] == false ? '' : employeeData['job_title'].toString(),
            department: employeeData['department_id'] != false
                ? employeeData['department_id'][1]
                : '',
            workEmail: employeeData['work_email'] == false ? '' : employeeData['work_email'].toString(),
            workPhone: employeeData['work_phone'] == false ? '' : employeeData['work_phone'].toString(),
            mobilePhone: employeeData['mobile_phone'] == false ? '' : employeeData['mobile_phone'].toString(),
          );

          return currentEmployee;
        } else {
          throw Exception('لم نجد بيانات للموظف');
        }
      } catch (e) {
        print('خطأ في getCurrentEmployee: $e');
        throw Exception('فشل جلب بيانات الموظف: $e');
      }
    }

    throw Exception('لا يوجد معرف موظف مخزن في الجلسة');
  }

  // تسجيل الخروج
  Future<void> logout() async {
    try {
      if (sessionId != null) {
        print('تسجيل الخروج، تدمير الجلسة: $sessionId');

        final url = '${baseUrl}web/session/destroy';
        await http.post(
          Uri.parse(url),
          headers: {
            'Content-Type': 'application/json',
            'Cookie': 'session_id=$sessionId',
          },
          body: jsonEncode({
            'jsonrpc': '2.0',
            'params': {},
          }),
        ).timeout(const Duration(seconds: 10));
      }
    } catch (e) {
      print('خطأ في logout: $e');
    } finally {
      sessionId = null;
      uid = null;
      employeeId = null;
      currentEmployee = null;

      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('session_id');
      await prefs.remove('uid');
      await prefs.remove('employee_id');
      await prefs.remove('user_session_id');
      await prefs.remove('user_uid');

      print('تم مسح بيانات الجلسة');
    }
  }

  // الحصول على حالة الحضور الحالية للموظف
  Future<Map<String, dynamic>> getCurrentAttendanceStatus(int employeeId) async {
    try {
      print('جلب حالة الحضور الحالية للموظف: $employeeId');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      final url = '${baseUrl}web/dataset/call_kw';
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.attendance',
            'method': 'search_read',
            'args': [
              [
                ['employee_id', '=', employeeId],
                ['check_out', '=', false]
              ],
              ['id', 'check_in', 'employee_id']
            ],
            'kwargs': {
              'limit': 1,
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة حالة الحضور: $result');

      if (result.containsKey('result')) {
        if (result['result'] != null && result['result'].isNotEmpty) {
          // يوجد سجل حضور بدون تسجيل انصراف
          return {
            'is_checked_in': true,
            'check_in': result['result'][0]['check_in'],
            'attendance_id': result['result'][0]['id'],
          };
        } else {
          // لا يوجد سجل حضور مفتوح
          return {'is_checked_in': false, 'check_in': null, 'attendance_id': null};
        }
      } else {
        throw Exception('خطأ في جلب حالة الحضور');
      }
    } catch (e) {
      print('خطأ في getCurrentAttendanceStatus: $e');
      return {'is_checked_in': false, 'check_in': null, 'attendance_id': null};
    }
  }

  // تسجيل الحضور
  Future<Map<String, dynamic>> checkIn(int employeeId) async {
    try {
      print('تسجيل حضور للموظف: $employeeId');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      final url = '${baseUrl}web/dataset/call_kw';
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.attendance',
            'method': 'mobile_check_in',
            'args': [employeeId],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة تسجيل الحضور: $result');

      if (result.containsKey('result') && result['result'] != null && result['result']['success']) {
        return {'success': true, 'attendance_id': result['result']['attendance_id']};
      } else if (result.containsKey('result') && result['result'] != null && result['result']['error']) {
        return {
          'success': false,
          'error': result['result']['error']
        };
      } else if (result.containsKey('error')) {
        return {
          'success': false,
          'error': result['error']['data']['message'] ?? 'حدث خطأ في تسجيل الحضور'
        };
      } else {
        throw Exception('خطأ في تسجيل الحضور');
      }
    } catch (e) {
      print('خطأ في checkIn: $e');
      return {'success': false, 'error': e.toString()};
    }
  }

  // تسجيل الانصراف
  Future<Map<String, dynamic>> checkOut(int employeeId) async {
    try {
      print('تسجيل انصراف للموظف: $employeeId');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      final url = '${baseUrl}web/dataset/call_kw';
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.attendance',
            'method': 'mobile_check_out',
            'args': [employeeId],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة تسجيل الانصراف: $result');

      if (result.containsKey('result') && result['result'] != null && result['result']['success']) {
        return {'success': true, 'duration': result['result']['duration']};
      } else if (result.containsKey('result') && result['result'] != null && result['result']['error']) {
        return {
          'success': false,
          'error': result['result']['error']
        };
      } else if (result.containsKey('error')) {
        return {
          'success': false,
          'error': result['error']['data']['message'] ?? 'حدث خطأ في تسجيل الانصراف'
        };
      } else {
        throw Exception('خطأ في تسجيل الانصراف');
      }
    } catch (e) {
      print('خطأ في checkOut: $e');
      return {'success': false, 'error': e.toString()};
    }
  }

  // الحصول على سجل الحضور للموظف
  Future<List<Map<String, dynamic>>> getAttendanceHistory(int employeeId) async {
    try {
      print('جلب سجل الحضور للموظف: $employeeId');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      final url = '${baseUrl}web/dataset/call_kw';
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.attendance',
            'method': 'get_employee_attendance_history',
            'args': [employeeId],
            'kwargs': {
              'limit': 10,
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة سجل الحضور: $result');

      if (result.containsKey('result') && result['result'] is List) {
        return List<Map<String, dynamic>>.from(result['result']);
      } else {
        throw Exception('خطأ في جلب سجل الحضور');
      }
    } catch (e) {
      print('خطأ في getAttendanceHistory: $e');
      return [];
    }
  }

  // الحصول على ملخص بيانات الموظف (وقت العمل وعدد الطلبات)
  Future<Map<String, dynamic>> getEmployeeSummary(int employeeId) async {
    try {
      print('جلب ملخص بيانات الموظف: $employeeId');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      final url = '${baseUrl}web/dataset/call_kw';
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.attendance',
            'method': 'get_employee_attendance_summary',
            'args': [employeeId],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة ملخص بيانات الموظف: $result');

      if (result.containsKey('result') && result['result'] is Map) {
        return Map<String, dynamic>.from(result['result']);
      } else {
        throw Exception('خطأ في جلب ملخص بيانات الموظف');
      }
    } catch (e) {
      print('خطأ في getEmployeeSummary: $e');
      return {
        'work_hours': '0:00',
        'request_count': 0,
      };
    }
  }
}

// ==================== دوال طلبات الإجازات ====================
Future<List<LeaveRequest>> getLeaveRequests(int employeeId) async {
  try {
    final url = '${baseUrl}web/dataset/call_kw';

    final response = await http.post(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Cookie': 'session_id=$sessionId',
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
              'number_of_days', 'name', 'state', 'create_date'
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
            // تحويل البيانات لتوافق النموذج
            final leaveData = {
              'id': item['id'],
              'employee_id': item['employee_id'] is List ? item['employee_id'][0] : item['employee_id'],
              'leave_type_id': item['holiday_status_id'] is List ? item['holiday_status_id'][0] : item['holiday_status_id'],
              'leave_type_name': item['holiday_status_id'] is List ? item['holiday_status_id'][1] : 'غير محدد',
              'date_from': item['date_from'],
              'date_to': item['date_to'],
              'number_of_days': item['number_of_days'] ?? 1,
              'reason': item['name'] ?? '',
              'state': item['state'] ?? 'draft',
              'state_text': _getStateText(item['state'] ?? 'draft'),
              'state_icon': _getStateIcon(item['state'] ?? 'draft'),
              'state_color': _getStateColor(item['state'] ?? 'draft'),
              'created_date': item['create_date'] ?? DateTime.now().toIso8601String(),
              'employee_name': item['employee_id'] is List ? item['employee_id'][1] : null,
            };

            requests.add(LeaveRequest.fromJson(leaveData));
          } catch (e) {
            print('خطأ في تحويل طلب إجازة: $e');
          }
        }

        return requests;
      }
    }

    // في حالة الفشل، إرجاع بيانات تجريبية
    return _generateMockLeaveRequests(employeeId);
  } catch (e) {
    print('خطأ في جلب طلبات الإجازات: $e');
    return _generateMockLeaveRequests(employeeId);
  }
}

/// إنشاء طلب إجازة جديد
Future<bool> createLeaveRequest({
  required int employeeId,
  required int leaveTypeId,
  required DateTime dateFrom,
  required DateTime dateTo,
  required String reason,
}) async {
  try {
    final url = '${baseUrl}web/dataset/call_kw';

    final response = await http.post(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Cookie': 'session_id=$sessionId',
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
            'date_from': dateFrom.toIso8601String(),
            'date_to': dateTo.toIso8601String(),
            'name': reason,
          }],
          'kwargs': {},
        },
        'id': DateTime.now().millisecondsSinceEpoch
      }),
    ).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final result = jsonDecode(response.body);
      return result['result'] != null;
    }

    return false;
  } catch (e) {
    print('خطأ في إنشاء طلب الإجازة: $e');
    return false;
  }
}

/// إلغاء طلب إجازة
Future<bool> cancelLeaveRequest(int requestId) async {
  try {
    final url = '${baseUrl}web/dataset/call_kw';

    final response = await http.post(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Cookie': 'session_id=$sessionId',
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
      return result['result'] != null;
    }

    return false;
  } catch (e) {
    print('خطأ في إلغاء طلب الإجازة: $e');
    return false;
  }
}

/// جلب أنواع الإجازات المتاحة
Future<List<LeaveType>> getLeaveTypes() async {
  try {
    final url = '${baseUrl}web/dataset/call_kw';

    final response = await http.post(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Cookie': 'session_id=$sessionId',
      },
      body: jsonEncode({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
          'model': 'hr.leave.type',
          'method': 'search_read',
          'args': [
            [['active', '=', true]],
            ['id', 'name', 'max_leaves', 'color_name']
          ],
          'kwargs': {},
        },
        'id': DateTime.now().millisecondsSinceEpoch
      }),
    ).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final result = jsonDecode(response.body);

      if (result['result'] != null && result['result'] is List) {
        final List<LeaveType> types = [];

        for (final item in result['result']) {
          types.add(LeaveType(
            id: item['id'],
            name: item['name'],
            maxDays: (item['max_leaves'] ?? 30).round(),
            color: item['color_name'] ?? '#2196F3',
            requiresApproval: true,
          ));
        }

        return types;
      }
    }

    // في حالة الفشل، إرجاع أنواع افتراضية
    return _getDefaultLeaveTypes();
  } catch (e) {
    print('خطأ في جلب أنواع الإجازات: $e');
    return _getDefaultLeaveTypes();
  }
}

// ==================== دوال مساعدة ====================

String _getStateText(String state) {
  switch (state) {
    case 'draft': return 'مسودة';
    case 'confirm': return 'قيد المراجعة';
    case 'validate1': return 'مراجعة أولى';
    case 'validate': return 'مقبولة';
    case 'refuse': return 'مرفوضة';
    case 'cancel': return 'ملغاة';
    default: return 'غير محدد';
  }
}

String _getStateIcon(String state) {
  switch (state) {
    case 'draft': return '📝';
    case 'confirm': return '⏳';
    case 'validate1': return '👁️';
    case 'validate': return '✅';
    case 'refuse': return '❌';
    case 'cancel': return '🚫';
    default: return '❓';
  }
}

String _getStateColor(String state) {
  switch (state) {
    case 'draft': return '#9E9E9E';
    case 'confirm': return '#FFA500';
    case 'validate1': return '#2196F3';
    case 'validate': return '#4CAF50';
    case 'refuse': return '#F44336';
    case 'cancel': return '#9E9E9E';
    default: return '#9E9E9E';
  }
}

/// أنواع إجازات افتراضية
List<LeaveType> _getDefaultLeaveTypes() {
  return [
    LeaveType(
      id: 1,
      name: 'إجازة سنوية',
      maxDays: 30,
      color: '#2196F3',
      requiresApproval: true,
    ),
    LeaveType(
      id: 2,
      name: 'إجازة مرضية',
      maxDays: 15,
      color: '#FF9800',
      requiresApproval: true,
    ),
    LeaveType(
      id: 3,
      name: 'إجازة طارئة',
      maxDays: 5,
      color: '#F44336',
      requiresApproval: true,
    ),
  ];
}

/// بيانات تجريبية لطلبات الإجازة
List<LeaveRequest> _generateMockLeaveRequests(int employeeId) {
  final now = DateTime.now();

  return [
    LeaveRequest(
      id: 1,
      employeeId: employeeId,
      leaveTypeId: 1,
      leaveTypeName: 'إجازة سنوية',
      dateFrom: now.add(Duration(days: 7)),
      dateTo: now.add(Duration(days: 9)),
      numberOfDays: 3,
      reason: 'إجازة للراحة والاستجمام',
      state: 'confirm',
      stateText: 'قيد المراجعة',
      stateIcon: '⏳',
      stateColor: '#FFA500',
      createdDate: now.subtract(Duration(days: 2)),
      employeeName: 'موظف تجريبي',
    ),
    LeaveRequest(
      id: 2,
      employeeId: employeeId,
      leaveTypeId: 2,
      leaveTypeName: 'إجازة مرضية',
      dateFrom: now.subtract(Duration(days: 5)),
      dateTo: now.subtract(Duration(days: 3)),
      numberOfDays: 3,
      reason: 'إجازة مرضية',
      state: 'validate',
      stateText: 'مقبولة',
      stateIcon: '✅',
      stateColor: '#4CAF50',
      createdDate: now.subtract(Duration(days: 7)),
      employeeName: 'موظف تجريبي',
      approvedBy: 'مدير الموارد البشرية',
      approvalDate: now.subtract(Duration(days: 6)),
    ),
  ];
}