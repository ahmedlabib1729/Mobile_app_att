import 'package:flutter/material.dart';
import 'home_page.dart';
import '../services/odoo_service.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({Key? key}) : super(key: key);

  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _rememberMe = false;
  bool _obscurePassword = true;  // متغير للتحكم في إظهار/إخفاء كلمة المرور
  bool _isLoading = false;

  // إنشاء خدمة Odoo
  final OdooService _odooService = OdooService(
    url: 'http://192.168.64.132:8018/', // قم بتغيير هذا الرابط حسب عنوان الخادم الخاص بك
    database: 'hr_emp',  // قم بتغيير هذا حسب اسم قاعدة البيانات الخاصة بك
  );

  @override
  void initState() {
    super.initState();
    _checkConnection();
  }

  // دالة للتأكد من الاتصال بالخادم عند بدء التطبيق
  Future<void> _checkConnection() async {
    try {
      // اختبار الاتصال بالخادم وطباعة النتيجة
      final bool serverConnected = await _odooService.testServerConnection();
      print('اختبار اتصال الخادم: ${serverConnected ? 'ناجح' : 'فشل'}');

      // اختبار واجهة API
      final bool apiConnected = await _odooService.testApiConnection();
      print('اختبار اتصال API: ${apiConnected ? 'ناجح' : 'فشل'}');

      // في حالة الفشل، عرض إشعار
      if (!serverConnected) {
        _showSnackBar('تعذر الاتصال بالخادم. تأكد من عنوان الخادم والاتصال بالإنترنت.');
      }
    } catch (e) {
      print('خطأ في اختبار الاتصال: $e');
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // عرض رسالة إشعار
  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  // دالة تسجيل الدخول
  Future<void> _loginUser() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    // عرض رسالة جاري تسجيل الدخول
    _showSnackBar('جاري تسجيل الدخول...');

    try {
      // طباعة بيانات تسجيل الدخول للتصحيح
      print('محاولة تسجيل دخول بالبيانات:');
      print('اسم المستخدم: ${_usernameController.text}');
      print('كلمة المرور: ${_passwordController.text.replaceAll(RegExp(r'.'), '*')}');

      // الاتصال بخادم Odoo واستخدام المستخدم المشترك
      final success = await _odooService.loginWithService();

      if (success) {
        print('تم تسجيل دخول المستخدم المشترك بنجاح، جاري المصادقة على الموظف...');

        // مصادقة الموظف باستخدام البريد الإلكتروني/اسم المستخدم وكلمة المرور
        final employee = await _odooService.authenticateEmployee(
          _usernameController.text,
          _passwordController.text,
        );

        if (employee != null) {
          print('تمت المصادقة على الموظف بنجاح: ${employee.name}');

          // الانتقال إلى الصفحة الرئيسية
          if (!mounted) return;
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => HomePage(
                odooService: _odooService,
                employee: employee, // إضافة المعامل المفقود
              ),
            ),
          );
        } else {
          // عرض رسالة خطأ
          _showSnackBar('بيانات تسجيل الدخول غير صحيحة');
        }
      } else {
        // عرض رسالة خطأ في الاتصال بالخادم
        _showSnackBar('تعذر الاتصال بالخادم');
      }
    } catch (e) {
      print('خطأ في تسجيل الدخول: $e');
      _showSnackBar('حدث خطأ: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.blue.shade800,
              Colors.indigo.shade900,
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Card(
                  elevation: 8,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // الشعار
                          const Icon(
                            Icons.lock_outlined,
                            size: 80,
                            color: Colors.blue,
                          ),
                          const SizedBox(height: 16),

                          // نص الترحيب
                          const Text(
                            'مرحباً بك',
                            style: TextStyle(
                              fontSize: 28,
                              fontWeight: FontWeight.bold,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'سجل الدخول للاستمرار',
                            style: TextStyle(
                              fontSize: 16,
                              color: Colors.grey,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 32),

                          // حقل اسم المستخدم
                          TextFormField(
                            controller: _usernameController,
                            decoration: const InputDecoration(
                              labelText: 'اسم المستخدم',
                              hintText: 'أدخل اسم المستخدم',
                              prefixIcon: Icon(Icons.person_outline),
                            ),
                            keyboardType: TextInputType.text,
                            textDirection: TextDirection.ltr,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'الرجاء إدخال اسم المستخدم';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),

                          // حقل كلمة المرور
                          TextFormField(
                            controller: _passwordController,
                            decoration: InputDecoration(
                              labelText: 'كلمة المرور',
                              hintText: 'أدخل كلمة المرور',
                              prefixIcon: const Icon(Icons.lock_outline),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_off : Icons.visibility,
                                ),
                                onPressed: () {
                                  setState(() {
                                    _obscurePassword = !_obscurePassword;
                                  });
                                },
                              ),
                            ),
                            obscureText: _obscurePassword,
                            textDirection: TextDirection.ltr,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'الرجاء إدخال كلمة المرور';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),

                          // تذكرني ونسيت كلمة المرور
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Checkbox(
                                    value: _rememberMe,
                                    onChanged: (value) {
                                      setState(() {
                                        _rememberMe = value ?? false;
                                      });
                                    },
                                  ),
                                  const Text('تذكرني'),
                                ],
                              ),
                              TextButton(
                                onPressed: () {
                                  // معالجة نسيت كلمة المرور
                                },
                                child: const Text('نسيت كلمة المرور؟'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 24),

                          // زر تسجيل الدخول
                          _isLoading
                              ? const CircularProgressIndicator()
                              : ElevatedButton(
                            onPressed: _loginUser,
                            child: const Text(
                              'تسجيل الدخول',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // خيار التسجيل
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Text('ليس لديك حساب؟'),
                              TextButton(
                                onPressed: () {
                                  // الانتقال إلى صفحة التسجيل
                                },
                                child: const Text(
                                  'سجل الآن',
                                  style: TextStyle(fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}