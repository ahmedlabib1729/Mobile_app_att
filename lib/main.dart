// main.dart - محدث مع دعم الطلبات - مُصحح
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'pages/login_page.dart';
import 'pages/home_page.dart';
import 'pages/attendance_screen.dart';
import 'pages/requests_screen.dart';
import 'pages/new_leave_request_screen.dart';
import 'pages/leave_request_details_screen.dart';
import 'services/offline_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // تهيئة بيانات التاريخ للغة العربية
  await initializeDateFormatting('ar', null);

  // بدء خدمة الوضع غير المتصل
  OfflineManager().startOfflineSupport();

  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'تطبيق الموظفين',
      debugShowCheckedModeBanner: false,

      // دعم اللغة العربية
      localizationsDelegates: [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: [
        Locale('ar', 'SA'), // العربية
        Locale('en', 'US'), // الإنجليزية
      ],
      locale: Locale('ar', 'SA'),

      // إعدادات المظهر
      theme: ThemeData(
        primarySwatch: Colors.blue,
        fontFamily: 'Cairo', // يمكن إضافة خط عربي

        // تخصيص الألوان
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),

        // تخصيص شريط التطبيق
        appBarTheme: AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Colors.black,
          elevation: 1,
          centerTitle: true,
        ),

        // تخصيص الأزرار
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.blue,
            foregroundColor: Colors.white,
            padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),

        // تخصيص البطاقات
        cardTheme: CardTheme(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),

        // تخصيص الإدخال
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          filled: true,
          fillColor: Colors.grey[50],
        ),
      ),

      // الصفحة الرئيسية
      home: LoginPage(),

      // المسارات - إزالة المسار المكسور
      routes: {
        '/login': (context) => LoginPage(),
        // إزالة '/home' المكسور
      },

      // معالج المسارات
      onGenerateRoute: (settings) {
        // استخراج المعاملات
        final args = settings.arguments as Map<String, dynamic>?;

        switch (settings.name) {
          case '/home':
            if (args != null) {
              return MaterialPageRoute(
                builder: (context) => HomePage(
                  odooService: args['odooService'],
                  employee: args['employee'],
                ),
              );
            }
            break;

          case '/attendance':
            if (args != null) {
              return MaterialPageRoute(
                builder: (context) => AttendanceScreen(
                  odooService: args['odooService'],
                  employee: args['employee'],
                ),
              );
            }
            break;

          case '/requests':
            if (args != null) {
              return MaterialPageRoute(
                builder: (context) => RequestsScreen(
                  odooService: args['odooService'],
                  employee: args['employee'],
                ),
              );
            }
            break;

          case '/new-leave-request':
            if (args != null) {
              return MaterialPageRoute(
                builder: (context) => NewLeaveRequestScreen(
                  odooService: args['odooService'],
                  employee: args['employee'],
                ),
              );
            }
            break;

          case '/leave-request-details':
            if (args != null) {
              return MaterialPageRoute(
                builder: (context) => LeaveRequestDetailsScreen(
                  request: args['request'],
                  odooService: args['odooService'],
                  employee: args['employee'],
                ),
              );
            }
            break;
        }

        // في حالة عدم وجود مسار
        return MaterialPageRoute(
          builder: (context) => Scaffold(
            appBar: AppBar(title: Text('خطأ')),
            body: Center(
              child: Text('الصفحة المطلوبة غير موجودة'),
            ),
          ),
        );
      },
    );
  }
}

// باقي الكود كما هو...
// ويدجت مساعد لعرض حالة الاتصال
class ConnectionStatusIndicator extends StatelessWidget {
  final bool isOnline;
  final int pendingActions;

  const ConnectionStatusIndicator({
    Key? key,
    required this.isOnline,
    required this.pendingActions,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (isOnline && pendingActions == 0) {
      return SizedBox.shrink(); // لا نعرض شيئاً إذا كان متصل وبدون أعمال مؤجلة
    }

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      margin: EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: isOnline ? Colors.orange : Colors.red,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isOnline ? Icons.sync : Icons.wifi_off,
            color: Colors.white,
            size: 16,
          ),
          SizedBox(width: 4),
          Text(
            isOnline
                ? 'مزامنة ($pendingActions)'
                : 'غير متصل',
            style: TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

// ويدجت لعرض رسائل التحديث
class UpdateSnackBar {
  static void show(BuildContext context, String message, {bool isSuccess = true}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isSuccess ? Icons.check_circle : Icons.error,
              color: Colors.white,
            ),
            SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: isSuccess ? Colors.green : Colors.red,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        duration: Duration(seconds: 3),
      ),
    );
  }
}

// ويدجت لعرض حوار التأكيد
class ConfirmationDialog {
  static Future<bool?> show({
    required BuildContext context,
    required String title,
    required String content,
    String confirmText = 'تأكيد',
    String cancelText = 'إلغاء',
    bool isDestructive = false,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(content),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(cancelText),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: isDestructive ? Colors.red : Colors.blue,
              foregroundColor: Colors.white,
            ),
            child: Text(confirmText),
          ),
        ],
      ),
    );
  }
}

// ويدجت لعرض حوار التحميل
class LoadingDialog {
  static Future<void> show(BuildContext context, String message) {
    return showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(message),
          ],
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }

  static void hide(BuildContext context) {
    Navigator.of(context).pop();
  }
}

// ثوابت التطبيق
class AppConstants {
  // ألوان التطبيق
  static const Color primaryColor = Colors.blue;
  static const Color secondaryColor = Colors.green;
  static const Color errorColor = Colors.red;
  static const Color warningColor = Colors.orange;

  // أحجام
  static const double defaultPadding = 16.0;
  static const double smallPadding = 8.0;
  static const double largePadding = 24.0;

  // مدد زمنية
  static const Duration defaultAnimationDuration = Duration(milliseconds: 300);
  static const Duration networkTimeout = Duration(seconds: 30);

  // نصوص
  static const String appName = 'تطبيق الموظفين';
  static const String noInternetMessage = 'لا يوجد اتصال بالإنترنت';
  static const String syncSuccessMessage = 'تمت المزامنة بنجاح';
  static const String syncErrorMessage = 'خطأ في المزامنة';
}