// main.dart - محدث مع دعم نظام اللغات الكامل
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';
import 'pages/login_page.dart';
import 'pages/home_page.dart';
import 'pages/attendance_screen.dart';
import 'pages/requests_screen.dart';
import 'pages/new_leave_request_screen.dart';
import 'pages/leave_request_details_screen.dart';
import 'services/offline_manager.dart';
import 'services/language_manager.dart';
import 'services/appointment_service.dart';
import 'package:intl/date_symbol_data_local.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // تهيئة بيانات التاريخ للغات
  await initializeDateFormatting('ar', null);
  await initializeDateFormatting('en', null);

  // تهيئة مدير اللغات
  await LanguageManager().initialize();

  await AppointmentService.initializeNotifications();

  // بدء خدمة الوضع غير المتصل
  OfflineManager().startOfflineSupport();

  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => LanguageManager(),
      child: Consumer<LanguageManager>(
        builder: (context, langManager, child) {
          return MaterialApp(
            title: 'Employee App',
            debugShowCheckedModeBanner: false,

            // دعم اللغات
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: const [
              Locale('en', 'US'), // الإنجليزية
              Locale('ar', 'SA'), // العربية
            ],
            locale: langManager.currentLocale,

            // إعدادات المظهر
            theme: ThemeData(
              primarySwatch: Colors.blue,
              fontFamily: langManager.isArabic ? 'Cairo' : null,

              colorScheme: ColorScheme.fromSeed(
                seedColor: Colors.blue,
                brightness: Brightness.light,
              ),

              appBarTheme: const AppBarTheme(
                backgroundColor: Colors.white,
                foregroundColor: Colors.black,
                elevation: 1,
                centerTitle: true,
              ),

              elevatedButtonTheme: ElevatedButtonThemeData(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),

              cardTheme: CardThemeData(
                elevation: 2,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),

              inputDecorationTheme: InputDecorationTheme(
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                filled: true,
                fillColor: Colors.grey[50],
              ),
            ),

            // تحديد اتجاه النصوص حسب اللغة
            builder: (context, child) {
              return Directionality(
                textDirection: langManager.isArabic
                    ? TextDirection.rtl
                    : TextDirection.ltr,
                child: child!,
              );
            },

            home: const LoginPage(),

            routes: {
              '/login': (context) => const LoginPage(),
            },

            onGenerateRoute: (settings) {
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

              return MaterialPageRoute(
                builder: (context) => Scaffold(
                  appBar: AppBar(
                    title: Text(context.lang.translate('error')),
                  ),
                  body: Center(
                    child: Text(
                      context.lang.isArabic
                          ? 'الصفحة المطلوبة غير موجودة'
                          : 'Page not found',
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
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
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      margin: const EdgeInsets.all(8),
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
          const SizedBox(width: 4),
          Text(
            isOnline
                ? '${context.lang.translate("sync")} ($pendingActions)'
                : context.lang.translate('offline'),
            style: const TextStyle(
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
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: isSuccess ? Colors.green : Colors.red,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        duration: const Duration(seconds: 3),
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
    String? confirmText,
    String? cancelText,
    bool isDestructive = false,
  }) {
    final lang = context.lang;
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
            child: Text(cancelText ?? lang.translate('cancel')),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: isDestructive ? Colors.red : Colors.blue,
              foregroundColor: Colors.white,
            ),
            child: Text(confirmText ?? lang.translate('confirm')),
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
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
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
}