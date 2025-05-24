// lib/services/odoo_service.dart - إصدار كامل ومُصحح مع دعم الصور
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/employee.dart';
import '../models/leave_type.dart';
import '../models/leave_request.dart';
import '../models/announcement.dart';

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

  // مصادقة الموظف باستخدام الـ mobile_username و mobile_pin مع جلب الصورة
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

        // إنشاء كائن الموظف مع معلومات الصورة
        currentEmployee = Employee(
          id: employeeData['id'],
          name: employeeData['name'],
          jobTitle: employeeData['job_title'] == false ? '' : employeeData['job_title'].toString(),
          department: employeeData['department'] == false ? '' : employeeData['department'].toString(),
          workEmail: employeeData['work_email'] == false ? '' : employeeData['work_email'].toString(),
          workPhone: employeeData['work_phone'] == false ? '' : employeeData['work_phone'].toString(),
          mobilePhone: '',
          // إضافة معلومات الصورة
          avatar128: employeeData['avatar_128'] != false && employeeData['avatar_128'] != null
              ? 'data:image/png;base64,${employeeData['avatar_128']}'
              : null,
          image1920: employeeData['image_1920'] != false && employeeData['image_1920'] != null
              ? 'data:image/png;base64,${employeeData['image_1920']}'
              : null,
          imageUrl: employeeData['avatar_128'] != false && employeeData['avatar_128'] != null
              ? 'data:image/png;base64,${employeeData['avatar_128']}'
              : null,
        );

        // حفظ الصورة محلياً للاستخدام بدون إنترنت
        if (employeeData['avatar_128'] != false && employeeData['avatar_128'] != null) {
          _cacheEmployeeImageFromBase64(employeeId!, employeeData['avatar_128']);
        }

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

  // الحصول على بيانات الموظف الحالي مع الصورة
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
                [
                  'id', 'name', 'job_title', 'department_id',
                  'work_email', 'work_phone', 'mobile_phone',
                  'avatar_128', 'image_1920' // إضافة حقول الصورة
                ]
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
            // إضافة معلومات الصورة
            avatar128: employeeData['avatar_128'] != false && employeeData['avatar_128'] != null
                ? 'data:image/png;base64,${employeeData['avatar_128']}'
                : null,
            image1920: employeeData['image_1920'] != false && employeeData['image_1920'] != null
                ? 'data:image/png;base64,${employeeData['image_1920']}'
                : null,
            imageUrl: employeeData['avatar_128'] != false && employeeData['avatar_128'] != null
                ? 'data:image/png;base64,${employeeData['avatar_128']}'
                : null,
          );

          // حفظ الصورة محلياً
          if (employeeData['avatar_128'] != false && employeeData['avatar_128'] != null) {
            _cacheEmployeeImageFromBase64(employeeData['id'], employeeData['avatar_128']);
          }

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

  // بناء رابط صورة الموظف
  String _buildImageUrl(int employeeId, String imageField) {
    return '${baseUrl}web/image?model=hr.employee&id=$employeeId&field=$imageField&unique=${DateTime.now().millisecondsSinceEpoch}';
  }

  // دالة عامة لبناء رابط الصورة (للاستخدام الخارجي)
  String buildImageUrl(int employeeId, String imageField) {
    return _buildImageUrl(employeeId, imageField);
  }

  // جلب صورة الموظف كـ bytes للحفظ المحلي
  Future<List<int>?> getEmployeeImageBytes(int employeeId, {String imageField = 'avatar_128'}) async {
    try {
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      final imageUrl = _buildImageUrl(employeeId, imageField);
      final response = await http.get(
        Uri.parse(imageUrl),
        headers: {
          'Cookie': 'session_id=$sessionId',
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return response.bodyBytes;
      } else {
        print('فشل في جلب صورة الموظف: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      print('خطأ في جلب صورة الموظف: $e');
      return null;
    }
  }

  // تحديث صورة الموظف (رفع صورة جديدة)
  Future<bool> updateEmployeeImage(int employeeId, List<int> imageBytes) async {
    try {
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      // تحويل الصورة إلى base64
      final base64Image = base64Encode(imageBytes);

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
            'method': 'write',
            'args': [
              [employeeId],
              {'image_1920': base64Image}
            ],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 30));

      final result = jsonDecode(response.body);

      if (result['result'] == true) {
        // تحديث الصورة محلياً أيضاً
        await cacheEmployeeImage(employeeId);
        return true;
      }

      return false;
    } catch (e) {
      print('خطأ في تحديث صورة الموظف: $e');
      return false;
    }
  }

  // التحقق من صحة رابط الصورة
  Future<bool> validateImageUrl(String imageUrl) async {
    try {
      final response = await http.head(
        Uri.parse(imageUrl),
        headers: {
          'Cookie': 'session_id=$sessionId',
        },
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      print('خطأ في التحقق من رابط الصورة: $e');
      return false;
    }
  }

  // حفظ الصورة محلياً (للاستخدام بدون إنترنت)
  Future<void> cacheEmployeeImage(int employeeId) async {
    try {
      final imageBytes = await getEmployeeImageBytes(employeeId);
      if (imageBytes != null) {
        final prefs = await SharedPreferences.getInstance();
        final base64Image = base64Encode(imageBytes);
        await prefs.setString('cached_image_$employeeId', base64Image);
        print('تم حفظ صورة الموظف $employeeId محلياً');
      }
    } catch (e) {
      print('خطأ في حفظ صورة الموظف محلياً: $e');
    }
  }

  // حفظ الصورة محلياً من Base64
  Future<void> _cacheEmployeeImageFromBase64(int employeeId, String base64Image) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('cached_image_$employeeId', base64Image);
      print('تم حفظ صورة الموظف $employeeId محلياً');
    } catch (e) {
      print('خطأ في حفظ صورة الموظف محلياً: $e');
    }
  }

  // استرجاع الصورة المحفوظة محلياً
  Future<String?> getCachedEmployeeImage(int employeeId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final base64Image = prefs.getString('cached_image_$employeeId');
      if (base64Image != null) {
        return 'data:image/jpeg;base64,$base64Image';
      }
      return null;
    } catch (e) {
      print('خطأ في استرجاع الصورة المحفوظة: $e');
      return null;
    }
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

      // مسح الصور المحفوظة محلياً
      final keys = prefs.getKeys();
      for (final key in keys) {
        if (key.startsWith('cached_image_')) {
          await prefs.remove(key);
        }
      }

      print('تم مسح بيانات الجلسة والصور المحفوظة');
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

  // جلب طلبات الإجازة للموظف
  Future<List<LeaveRequest>> getLeaveRequests(int employeeId) async {
    try {
      print('جلب طلبات الإجازة للموظف: $employeeId');

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
            'model': 'hr.leave',
            'method': 'search_read',
            'args': [
              [['employee_id', '=', employeeId]],
              [
                'id', 'name', 'holiday_status_id', 'request_date_from',
                'request_date_to', 'number_of_days', 'state'
              ]
            ],
            'kwargs': {
              'order': 'create_date desc',
              'limit': 20,
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة طلبات الإجازة: $result');

      if (result.containsKey('result') && result['result'] is List) {
        List<LeaveRequest> leaveRequests = [];
        for (var item in result['result']) {
          try {
            // معالجة القيم الفارغة أو false
            String requestName = '';
            if (item['name'] != null && item['name'] != false) {
              requestName = item['name'].toString();
            }

            // معالجة holiday_status_id
            int leaveTypeId = 0;
            String leaveTypeName = '';
            if (item['holiday_status_id'] != null && item['holiday_status_id'] != false) {
              if (item['holiday_status_id'] is List && item['holiday_status_id'].length >= 2) {
                leaveTypeId = item['holiday_status_id'][0];
                leaveTypeName = item['holiday_status_id'][1];
              }
            }

            // معالجة التواريخ
            DateTime dateFrom = DateTime.now();
            DateTime dateTo = DateTime.now();
            try {
              dateFrom = DateTime.parse(item['request_date_from']);
              dateTo = DateTime.parse(item['request_date_to']);
            } catch (e) {
              print('خطأ في تحويل التاريخ: $e');
            }

            leaveRequests.add(LeaveRequest(
              id: item['id'] ?? 0,
              employeeId: employeeId,
              leaveTypeId: leaveTypeId,
              leaveTypeName: leaveTypeName,
              dateFrom: dateFrom,
              dateTo: dateTo,
              numberOfDays: (item['number_of_days'] ?? 0).toDouble(),
              reason: requestName,
              state: item['state'] ?? 'draft',
              stateText: _getStateText(item['state'] ?? 'draft'),
              stateIcon: _getStateIcon(item['state'] ?? 'draft'),
              stateColor: _getStateColor(item['state'] ?? 'draft'),
              createdDate: DateTime.now(),
            ));
          } catch (e) {
            print('خطأ في معالجة طلب إجازة واحد: $e');
            print('البيانات التي سببت الخطأ: $item');
            // تجاهل هذا العنصر والمتابعة مع الباقي
          }
        }
        return leaveRequests;
      } else {
        throw Exception('خطأ في جلب طلبات الإجازة');
      }
    } catch (e) {
      print('خطأ في getLeaveRequests: $e');
      return [];
    }
  }

  // جلب أنواع الإجازات المتاحة
  Future<List<LeaveType>> getLeaveTypes() async {
    try {
      print('جلب أنواع الإجازات المتاحة');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      // محاولة طريقة مختلفة للحصول على أنواع الإجازات
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
            'args': [],  // إزالة الشروط
            'kwargs': {
              'fields': ['id', 'name', 'time_type', 'requires_allocation'],
              'context': {},
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة أنواع الإجازات: $result');

      // إذا فشلت المحاولة الأولى، جرب طريقة أخرى
      if (result.containsKey('error')) {
        print('خطأ في جلب أنواع الإجازات، محاولة طريقة بديلة...');

        // محاولة استخدام search ثم read
        final searchResponse = await http.post(
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
              'method': 'search',
              'args': [[]],
              'kwargs': {},
            },
            'id': DateTime.now().millisecondsSinceEpoch
          }),
        ).timeout(const Duration(seconds: 15));

        final searchResult = jsonDecode(searchResponse.body);

        if (searchResult['result'] != null && searchResult['result'] is List) {
          final ids = List<int>.from(searchResult['result']);

          if (ids.isNotEmpty) {
            // الآن اقرأ البيانات
            final readResponse = await http.post(
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
                  'method': 'read',
                  'args': [ids, ['id', 'name']],
                  'kwargs': {},
                },
                'id': DateTime.now().millisecondsSinceEpoch
              }),
            ).timeout(const Duration(seconds: 15));

            final readResult = jsonDecode(readResponse.body);

            if (readResult['result'] != null && readResult['result'] is List) {
              List<LeaveType> leaveTypes = [];
              for (var item in readResult['result']) {
                leaveTypes.add(LeaveType(
                  id: item['id'] ?? 0,
                  name: item['name'] ?? 'غير محدد',
                  maxDays: 30, // قيمة افتراضية
                  color: '#2196F3', // قيمة افتراضية
                  requiresApproval: true, // قيمة افتراضية
                  timeType: 'leave',
                  allocationType: 'no',
                ));
              }
              return leaveTypes;
            }
          }
        }

        // إذا فشلت كل المحاولات، أرجع قائمة افتراضية
        print('فشلت جميع محاولات جلب أنواع الإجازات، استخدام القيم الافتراضية');
        return _getDefaultLeaveTypes();
      }

      if (result.containsKey('result') && result['result'] is List) {
        List<LeaveType> leaveTypes = [];
        for (var item in result['result']) {
          try {
            leaveTypes.add(LeaveType(
              id: item['id'] ?? 0,
              name: item['name'] ?? 'غير محدد',
              maxDays: 30, // قيمة افتراضية
              color: '#2196F3', // قيمة افتراضية
              requiresApproval: true, // قيمة افتراضية
              timeType: item['time_type'] ?? 'leave',
              allocationType: item['requires_allocation'] ?? 'no',
            ));
          } catch (e) {
            print('خطأ في معالجة نوع إجازة: $e');
          }
        }

        // إذا كانت القائمة فارغة، استخدم القيم الافتراضية
        if (leaveTypes.isEmpty) {
          return _getDefaultLeaveTypes();
        }

        return leaveTypes;
      } else {
        // استخدام قائمة افتراضية
        return _getDefaultLeaveTypes();
      }
    } catch (e) {
      print('خطأ في getLeaveTypes: $e');
      // إرجاع قائمة افتراضية في حالة الخطأ
      return _getDefaultLeaveTypes();
    }
  }

  // قائمة أنواع الإجازات الافتراضية
  List<LeaveType> _getDefaultLeaveTypes() {
    return [
      LeaveType(
        id: 1,
        name: 'إجازة سنوية',
        maxDays: 30,
        color: '#4CAF50',
        requiresApproval: true,
        timeType: 'leave',
        allocationType: 'no',
      ),
      LeaveType(
        id: 2,
        name: 'إجازة مرضية',
        maxDays: 15,
        color: '#F44336',
        requiresApproval: true,
        timeType: 'leave',
        allocationType: 'no',
      ),
      LeaveType(
        id: 3,
        name: 'إجازة طارئة',
        maxDays: 5,
        color: '#FF9800',
        requiresApproval: true,
        timeType: 'leave',
        allocationType: 'no',
      ),
    ];
  }

  // إنشاء طلب إجازة جديد
  Future<Map<String, dynamic>> createLeaveRequest({
    required int employeeId,
    required int leaveTypeId,
    required DateTime dateFrom,
    required DateTime dateTo,
    required String description,
  }) async {
    try {
      print('إنشاء طلب إجازة جديد للموظف: $employeeId');

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
            'model': 'hr.leave',
            'method': 'create',
            'args': [
              {
                'employee_id': employeeId,
                'holiday_status_id': leaveTypeId,
                'request_date_from': dateFrom.toIso8601String(),
                'request_date_to': dateTo.toIso8601String(),
                'name': description,
              }
            ],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة إنشاء طلب الإجازة: $result');

      if (result.containsKey('result') && result['result'] is int) {
        return {
          'success': true,
          'leave_request_id': result['result'],
          'message': 'تم إنشاء طلب الإجازة بنجاح'
        };
      } else if (result.containsKey('error')) {
        return {
          'success': false,
          'error': result['error']['data']['message'] ?? 'حدث خطأ في إنشاء طلب الإجازة'
        };
      } else {
        throw Exception('خطأ في إنشاء طلب الإجازة');
      }
    } catch (e) {
      print('خطأ في createLeaveRequest: $e');
      return {
        'success': false,
        'error': e.toString()
      };
    }
  }

  // إلغاء طلب إجازة
  Future<Map<String, dynamic>> cancelLeaveRequest(int leaveRequestId) async {
    try {
      print('إلغاء طلب الإجازة: $leaveRequestId');

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
            'model': 'hr.leave',
            'method': 'action_refuse',
            'args': [[leaveRequestId]],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة إلغاء طلب الإجازة: $result');

      if (result.containsKey('result')) {
        return {
          'success': true,
          'message': 'تم إلغاء طلب الإجازة بنجاح'
        };
      } else if (result.containsKey('error')) {
        return {
          'success': false,
          'error': result['error']['data']['message'] ?? 'حدث خطأ في إلغاء طلب الإجازة'
        };
      } else {
        throw Exception('خطأ في إلغاء طلب الإجازة');
      }
    } catch (e) {
      print('خطأ في cancelLeaveRequest: $e');
      return {
        'success': false,
        'error': e.toString()
      };
    }
  }

  // جلب ملخص الحضور للموظف
  Future<Map<String, dynamic>> getAttendanceSummary(int employeeId) async {
    try {
      print('جلب ملخص الحضور للموظف: $employeeId');

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
      print('استجابة ملخص الحضور: $result');

      if (result.containsKey('result') && result['result'] is Map) {
        return Map<String, dynamic>.from(result['result']);
      } else {
        // إذا لم تكن الدالة متاحة، قم بحساب الملخص يدوياً
        return await _calculateAttendanceSummary(employeeId);
      }
    } catch (e) {
      print('خطأ في getAttendanceSummary: $e');
      // حساب الملخص يدوياً في حالة الخطأ
      return await _calculateAttendanceSummary(employeeId);
    }
  }

  // حساب ملخص الحضور يدوياً
  Future<Map<String, dynamic>> _calculateAttendanceSummary(int employeeId) async {
    try {
      // جلب سجلات الحضور للشهر الحالي
      final now = DateTime.now();
      final firstDayOfMonth = DateTime(now.year, now.month, 1);
      final lastDayOfMonth = DateTime(now.year, now.month + 1, 0);

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
                ['check_in', '>=', firstDayOfMonth.toIso8601String()],
                ['check_in', '<=', lastDayOfMonth.toIso8601String()]
              ],
              ['check_in', 'check_out', 'worked_hours']
            ],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);

      if (result.containsKey('result') && result['result'] is List) {
        final attendanceRecords = result['result'];
        int totalDays = attendanceRecords.length;
        double totalHours = 0;

        for (var record in attendanceRecords) {
          totalHours += (record['worked_hours'] ?? 0).toDouble();
        }

        return {
          'total_days': totalDays,
          'total_hours': totalHours,
          'average_hours': totalDays > 0 ? totalHours / totalDays : 0,
          'month': now.month,
          'year': now.year,
        };
      }

      return {
        'total_days': 0,
        'total_hours': 0,
        'average_hours': 0,
        'month': now.month,
        'year': now.year,
      };
    } catch (e) {
      print('خطأ في _calculateAttendanceSummary: $e');
      return {
        'total_days': 0,
        'total_hours': 0,
        'average_hours': 0,
        'month': DateTime.now().month,
        'year': DateTime.now().year,
      };
    }
  }

  // جلب الإشعارات
  Future<List<Map<String, dynamic>>> getNotifications(int employeeId) async {
    try {
      print('جلب الإشعارات للموظف: $employeeId');

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
            'model': 'mail.message',
            'method': 'search_read',
            'args': [
              [
                ['res_model', '=', 'hr.employee'],
                ['res_id', '=', employeeId],
                ['message_type', '=', 'notification']
              ],
              ['id', 'subject', 'body', 'date', 'author_id']
            ],
            'kwargs': {
              'order': 'date desc',
              'limit': 10,
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة الإشعارات: $result');

      if (result.containsKey('result') && result['result'] is List) {
        return List<Map<String, dynamic>>.from(result['result']);
      } else {
        return [];
      }
    } catch (e) {
      print('خطأ في getNotifications: $e');
      return [];
    }
  }

  // تحديث بيانات الموظف
  Future<bool> updateEmployeeInfo({
    required int employeeId,
    String? workPhone,
    String? mobilePhone,
    String? workEmail,
  }) async {
    try {
      print('تحديث بيانات الموظف: $employeeId');

      // التأكد من وجود جلسة نشطة
      if (sessionId == null) {
        bool success = await loginWithService();
        if (!success) {
          throw Exception('فشل تسجيل الدخول');
        }
      }

      Map<String, dynamic> updateData = {};
      if (workPhone != null) updateData['work_phone'] = workPhone;
      if (mobilePhone != null) updateData['mobile_phone'] = mobilePhone;
      if (workEmail != null) updateData['work_email'] = workEmail;

      if (updateData.isEmpty) {
        return true; // لا يوجد شيء للتحديث
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
            'method': 'write',
            'args': [
              [employeeId],
              updateData
            ],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch
        }),
      ).timeout(const Duration(seconds: 15));

      final result = jsonDecode(response.body);
      print('استجابة تحديث بيانات الموظف: $result');

      if (result.containsKey('result') && result['result'] == true) {
        // تحديث البيانات محلياً
        if (currentEmployee != null && currentEmployee!.id == employeeId) {
          currentEmployee = currentEmployee!.copyWith(
            workPhone: workPhone ?? currentEmployee!.workPhone,
            mobilePhone: mobilePhone ?? currentEmployee!.mobilePhone,
            workEmail: workEmail ?? currentEmployee!.workEmail,
          );
        }
        return true;
      } else {
        return false;
      }
    } catch (e) {
      print('خطأ في updateEmployeeInfo: $e');
      return false;
    }
  }

  // التحقق من صحة الجلسة
  Future<bool> isSessionValid() async {
    try {
      if (sessionId == null || uid == null) {
        return false;
      }

      final url = '${baseUrl}web/session/get_session_info';
      final response = await http.post(
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

      final result = jsonDecode(response.body);
      return result.containsKey('result') &&
          result['result'] != null &&
          result['result']['uid'] == uid;
    } catch (e) {
      print('خطأ في التحقق من صحة الجلسة: $e');
      return false;
    }
  }

  // تجديد الجلسة إذا لزم الأمر
  Future<bool> refreshSessionIfNeeded() async {
    bool isValid = await isSessionValid();
    if (!isValid) {
      print('الجلسة غير صحيحة، محاولة تجديدها...');
      return await loginWithService();
    }
    return true;
  }

  // استخراج أنواع الإجازات من طلبات الإجازات الموجودة
  Future<List<LeaveType>> getLeaveTypesFromRequests(List<LeaveRequest> requests) async {
    try {
      Map<int, LeaveType> typesMap = {};

      // الألوان الافتراضية لأنواع الإجازات
      final colors = ['#4CAF50', '#F44336', '#FF9800', '#2196F3', '#9C27B0', '#00BCD4'];
      int colorIndex = 0;

      for (var request in requests) {
        if (request.leaveTypeId > 0 && !typesMap.containsKey(request.leaveTypeId)) {
          typesMap[request.leaveTypeId] = LeaveType(
            id: request.leaveTypeId,
            name: request.leaveTypeName,
            maxDays: 30, // قيمة افتراضية
            color: colors[colorIndex % colors.length],
            requiresApproval: true,
            timeType: 'leave',
            allocationType: 'no',
          );
          colorIndex++;
        }
      }

      // إذا لم نجد أي أنواع، استخدم القائمة الافتراضية
      if (typesMap.isEmpty) {
        return _getDefaultLeaveTypes();
      }

      return typesMap.values.toList();
    } catch (e) {
      print('خطأ في استخراج أنواع الإجازات: $e');
      return _getDefaultLeaveTypes();
    }
  }



  String _getStateText(String state) {
    switch (state) {
      case 'draft': return 'Draft';
      case 'confirm': return 'Pending Review';
      case 'validate1': return 'First Approval';
      case 'validate': return 'Approved';
      case 'refuse': return 'Rejected';
      case 'cancel': return 'Cancelled';
      default: return 'Not specified';
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

  // أضف هذه الدوال في ملف services/odoo_service.dart


  // دوال الإعلانات - باستخدام نفس أسلوب authenticate

  // ============ دوال الإعلانات ============

  Future<List<Announcement>> getAnnouncements(int employeeId, {int limit = 20, int offset = 0}) async {
    try {
      print('جلب الإعلانات للموظف: $employeeId');

      final uri = Uri.parse('$baseUrl/api/mobile/announcements/list');
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: json.encode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'employee_id': employeeId,
            'limit': limit,
            'offset': offset,
          },
          'id': DateTime.now().millisecondsSinceEpoch,
        }),
      );

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        final jsonResponse = json.decode(response.body);
        print('Decoded response: $jsonResponse');

        // معالجة أنواع مختلفة من الـ responses
        if (jsonResponse['result'] != null) {
          final result = jsonResponse['result'];

          // إذا كان success/announcements structure
          if (result is Map && result['success'] == true && result['announcements'] != null) {
            final announcementsData = result['announcements'];
            if (announcementsData is List) {
              return announcementsData
                  .map((data) => Announcement.fromJson(data))
                  .toList();
            }
          }

          // إذا كان List مباشرة
          if (result is List) {
            return result
                .map((data) => Announcement.fromJson(data))
                .toList();
          }

          // إذا كان error
          if (result is Map && result['error'] != null) {
            print('API Error: ${result['error']}');
            return [];
          }
        }

        // إذا كان error في الـ response
        if (jsonResponse['error'] != null) {
          print('JSON-RPC Error: ${jsonResponse['error']}');
          return [];
        }
      }

      return [];
    } catch (e, stackTrace) {
      print('خطأ في جلب الإعلانات: $e');
      print('Stack trace: $stackTrace');
      return [];
    }
  }

  // جلب تفاصيل إعلان
  Future<Map<String, dynamic>> getAnnouncementDetail(int announcementId, int employeeId) async {
    try {
      print('جلب تفاصيل الإعلان: $announcementId');

      final uri = Uri.parse('$baseUrl/api/mobile/announcements/detail');
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: json.encode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.announcement',
            'method': 'get_announcement_detail',
            'args': [announcementId, employeeId],
            'kwargs': {},
          },
          'id': DateTime.now().millisecondsSinceEpoch,
        }),
      );

      if (response.statusCode == 200) {
        final jsonResponse = json.decode(response.body);

        if (jsonResponse['result'] != null) {
          return jsonResponse['result'] is Map
              ? jsonResponse['result']
              : {};
        }
      }

      return {};
    } catch (e) {
      print('خطأ في جلب تفاصيل الإعلان: $e');
      return {};
    }
  }

  // تسجيل قراءة الإعلان
  Future<bool> markAnnouncementAsRead(int announcementId, int employeeId) async {
    try {
      print('تسجيل قراءة الإعلان: $announcementId');

      final uri = Uri.parse('$baseUrl/api/mobile/announcements/mark_read');
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: json.encode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.announcement',
            'method': 'mark_as_read',
            'args': [[announcementId]],
            'kwargs': {'employee_id': employeeId},
          },
          'id': DateTime.now().millisecondsSinceEpoch,
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      print('خطأ في تسجيل قراءة الإعلان: $e');
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> getAnnouncementCategories() async {
    try {
      print('جلب تصنيفات الإعلانات');

      final uri = Uri.parse('$baseUrl/api/mobile/announcements/categories');
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: json.encode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {},
          'id': DateTime.now().millisecondsSinceEpoch,
        }),
      );

      if (response.statusCode == 200) {
        final jsonResponse = json.decode(response.body);

        // التعديل هنا - استخراج categories من result
        if (jsonResponse['result'] != null && jsonResponse['result']['success'] == true) {
          final categoriesData = jsonResponse['result']['categories'];
          if (categoriesData != null && categoriesData is List) {
            return List<Map<String, dynamic>>.from(categoriesData);
          }
        }
      }

      // إذا فشل، نرجع القيم الافتراضية
      return [
        {'id': 'all', 'name': 'جميع الإعلانات', 'icon': '📢', 'color': '#2196F3'},
        {'id': 'general', 'name': 'إعلانات عامة', 'icon': '📣', 'color': '#4CAF50'},
        {'id': 'department', 'name': 'إعلانات القسم', 'icon': '🏢', 'color': '#FF9800'},
        {'id': 'urgent', 'name': 'إعلانات عاجلة', 'icon': '🚨', 'color': '#F44336'},
        {'id': 'personal', 'name': 'إعلانات شخصية', 'icon': '👤', 'color': '#9C27B0'}
      ];
    } catch (e) {
      print('خطأ في جلب التصنيفات: $e');
      return [];
    }
  }

  // البحث في الإعلانات
  Future<List<Announcement>> searchAnnouncements(
      int employeeId,
      String searchTerm, {
        String category = 'all',
        int limit = 20,
      }) async {
    try {
      print('البحث في الإعلانات: $searchTerm');

      final uri = Uri.parse('$baseUrl/api/mobile/announcements/search');
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Cookie': 'session_id=$sessionId',
        },
        body: json.encode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': {
            'model': 'hr.announcement',
            'method': 'search_announcements',
            'args': [employeeId],
            'kwargs': {
              'search_term': searchTerm,
              'category': category,
              'limit': limit,
            },
          },
          'id': DateTime.now().millisecondsSinceEpoch,
        }),
      );

      if (response.statusCode == 200) {
        final jsonResponse = json.decode(response.body);

        if (jsonResponse['result'] != null) {
          final List<dynamic> resultsData = jsonResponse['result'] is List
              ? jsonResponse['result']
              : (jsonResponse['result']['results'] ?? []);

          return resultsData
              .map((data) => Announcement.fromJson(data))
              .toList();
        }
      }

      return [];
    } catch (e) {
      print('خطأ في البحث: $e');
      return [];
    }
  }
}