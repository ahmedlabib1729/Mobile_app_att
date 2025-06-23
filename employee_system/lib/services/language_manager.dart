// lib/services/language_manager.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class LanguageManager extends ChangeNotifier {
  static const String _languageKey = 'selected_language';

  Locale _currentLocale = const Locale('en', 'US');
  Map<String, dynamic> _localizedStrings = {};

  Locale get currentLocale => _currentLocale;
  bool get isArabic => _currentLocale.languageCode == 'ar';

  // Singleton pattern
  static final LanguageManager _instance = LanguageManager._internal();
  factory LanguageManager() => _instance;
  LanguageManager._internal();

  // تهيئة اللغة
  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final savedLanguage = prefs.getString(_languageKey) ?? 'en';

    _currentLocale = Locale(savedLanguage, savedLanguage == 'ar' ? 'SA' : 'US');
    await loadLanguage();
  }

  // تحميل ملف اللغة
  Future<void> loadLanguage() async {
    // في الإنتاج، يفضل تحميل من ملفات JSON
    // لكن هنا سنستخدم Map مباشرة للبساطة
    if (_currentLocale.languageCode == 'ar') {
      _localizedStrings = _arabicStrings;
    } else {
      _localizedStrings = _englishStrings;
    }
    notifyListeners();
  }

  // تغيير اللغة
  Future<void> changeLanguage(String languageCode) async {
    if (languageCode == _currentLocale.languageCode) return;

    _currentLocale = Locale(languageCode, languageCode == 'ar' ? 'SA' : 'US');

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_languageKey, languageCode);

    await loadLanguage();
  }

  // الحصول على النص المترجم
  String translate(String key) {
    return _localizedStrings[key] ?? key;
  }

  // اختصار للترجمة
  String get(String key) => translate(key);
}

// النصوص الإنجليزية
final Map<String, dynamic> _englishStrings = {
  // Login Page
  'login': 'LOGIN',
  'username': 'Username',
  'password': 'Password',
  'remember_me': 'Remember me',
  'please_enter_username': 'Please enter your username',
  'please_enter_password': 'Please enter your password',
  'signing_in': 'Signing you in...',
  'invalid_credentials': 'Invalid username or password',
  'connection_error': 'Unable to connect to server',
  'powered_by': 'Powered BY ERP Accounting and Auditing',

  // Home Page
  'welcome': 'Welcome',
  'home': 'Home',
  'todays_working_hours': "Today's Working Hours",
  'check_in': 'Check In',
  'check_out': 'Check Out',
  'manage_attendance': 'Manage Attendance',
  'leaves': 'Leaves',
  'announcements': 'Announcements',
  'additional_info': 'Additional Information',
  'online': 'Online',
  'offline': 'Offline',
  'logout': 'Logout',
  'logout_confirmation': 'Logout Confirmation',
  'logout_message': 'Are you sure you want to logout?',
  'cancel': 'Cancel',
  'confirm': 'Confirm',
  'loading_data': 'Loading data...',
  'refresh': 'Refresh',
  'profile': 'Profile',

  // General
  'error': 'Error',
  'success': 'Success',
  'warning': 'Warning',
  'info': 'Info',
  'ok': 'OK',
  'yes': 'Yes',
  'no': 'No',
  'save': 'Save',
  'delete': 'Delete',
  'edit': 'Edit',
  'close': 'Close',
  'search': 'Search',
  'filter': 'Filter',
  'sort': 'Sort',
  'data_synced': 'Data synchronized successfully',
  'sync_error': 'Error syncing data',
  'no_internet': 'No internet connection',
  'retry': 'Retry',
  'language': 'Language',
  'arabic': 'العربية',
  'english': 'English',

  // Leave Requests Page
  'leave_requests': 'Leave Requests',
  'rejected': 'Rejected',
  'approved': 'Approved',
  'pending': 'Pending',
  'all': 'All',
  'one_day': 'One Day',
  'paid_time_off': 'Paid Time Off',
  'new_request': 'New Request',
  'test': 'test',
  'days': 'Days',
  'day': 'Day',
  'leave_type': 'Leave Type',
  'start_date': 'Start Date',
  'end_date': 'End Date',
  'reason': 'Reason',
  'status': 'Status',
  'duration': 'Duration',
  'sick_leave': 'Sick Leave',
  'annual_leave': 'Annual Leave',
  'emergency_leave': 'Emergency Leave',
  'unpaid_leave': 'Unpaid Leave',
  'submit_request': 'Submit Request',
  'cancel_request': 'Cancel Request',
  'view_details': 'View Details',

  // Announcements Page
  'search_announcements': 'Search announcements',
  'new': 'New',
  'no_announcements': 'No announcements available',
  'announcement_details': 'Announcement Details',
  'published_date': 'Published Date',
  'important': 'Important',
  'mark_as_read': 'Mark as Read',
  'unread': 'Unread',

  // Payslips Page
  'payslips': 'Payslips',
  'payslip': 'Payslip',
  'payslip_details': 'Payslip Details',
  'salary_summary': 'Salary Summary',
  'salary_breakdown': 'Salary Breakdown',
  'basic_salary': 'Basic Salary',
  'gross_salary': 'Gross Salary',
  'net_salary': 'Net Salary',
  'allowances': 'Allowances',
  'deductions': 'Deductions',
  'total_allowances': 'Total Allowances',
  'total_deductions': 'Total Deductions',
  'housing_allowance': 'Housing Allowance',
  'transportation_allowance': 'Transportation Allowance',
  'food_allowance': 'Food Allowance',
  'phone_allowance': 'Phone Allowance',
  'other_allowances': 'Other Allowances',
  'social_insurance': 'Social Insurance',
  'taxes': 'Taxes',
  'loans': 'Loans',
  'absence_deduction': 'Absence Deduction',
  'other_deductions': 'Other Deductions',
  'total_received': 'Total Received',
  'average_salary': 'Average Salary',
  'last_payment': 'Last Payment',
  'payment_date': 'Payment Date',
  'working_days': 'Working Days',
  'period': 'Period',
  'bank': 'Bank',
  'account': 'Account',
  'notes': 'Notes',
  'download': 'Download',
  'download_failed': 'Download failed',
  'no_payslips': 'No payslips found',
  'no_data': 'No data available',
  'paid': 'Paid',
  'under_review': 'Under Review',
  'draft': 'Draft',
  'done': 'Done',
  'verify': 'Verify',
  'cancel': 'Cancel',
  'egp': 'EGP',
  'loading': 'Loading...',
};

// النصوص العربية
final Map<String, dynamic> _arabicStrings = {
  // صفحة تسجيل الدخول
  'login': 'تسجيل الدخول',
  'username': 'اسم المستخدم',
  'password': 'كلمة المرور',
  'remember_me': 'تذكرني',
  'please_enter_username': 'من فضلك أدخل اسم المستخدم',
  'please_enter_password': 'من فضلك أدخل كلمة المرور',
  'signing_in': 'جاري تسجيل الدخول...',
  'invalid_credentials': 'اسم المستخدم أو كلمة المرور غير صحيحة',
  'connection_error': 'غير قادر على الاتصال بالخادم',
  'powered_by': 'مدعوم من ERP للمحاسبة والمراجعة',

  // الصفحة الرئيسية
  'welcome': 'مرحباً',
  'home': 'الرئيسية',
  'todays_working_hours': 'ساعات العمل اليوم',
  'check_in': 'تسجيل الحضور',
  'check_out': 'تسجيل الانصراف',
  'manage_attendance': 'إدارة الحضور',
  'leaves': 'الإجازات',
  'announcements': 'الإعلانات',
  'additional_info': 'معلومات إضافية',
  'online': 'متصل',
  'offline': 'غير متصل',
  'logout': 'تسجيل الخروج',
  'logout_confirmation': 'تأكيد تسجيل الخروج',
  'logout_message': 'هل أنت متأكد من تسجيل الخروج؟',
  'cancel': 'إلغاء',
  'confirm': 'تأكيد',
  'loading_data': 'جاري تحميل البيانات...',
  'refresh': 'تحديث',
  'profile': 'الملف الشخصي',

  // عام
  'error': 'خطأ',
  'success': 'نجاح',
  'warning': 'تحذير',
  'info': 'معلومة',
  'ok': 'موافق',
  'yes': 'نعم',
  'no': 'لا',
  'save': 'حفظ',
  'delete': 'حذف',
  'edit': 'تعديل',
  'close': 'إغلاق',
  'search': 'بحث',
  'filter': 'تصفية',
  'sort': 'ترتيب',
  'data_synced': 'تمت مزامنة البيانات بنجاح',
  'sync_error': 'خطأ في مزامنة البيانات',
  'no_internet': 'لا يوجد اتصال بالإنترنت',
  'retry': 'إعادة المحاولة',
  'language': 'اللغة',
  'arabic': 'العربية',
  'english': 'English',

  // صفحة طلبات الإجازة
  'leave_requests': 'طلبات الإجازة',
  'rejected': 'مرفوضة',
  'approved': 'موافق عليها',
  'pending': 'قيد الانتظار',
  'all': 'الكل',
  'one_day': 'يوم واحد',
  'paid_time_off': 'إجازة مدفوعة',
  'new_request': 'طلب جديد',
  'test': 'اختبار',
  'days': 'أيام',
  'day': 'يوم',
  'leave_type': 'نوع الإجازة',
  'start_date': 'تاريخ البداية',
  'end_date': 'تاريخ النهاية',
  'reason': 'السبب',
  'status': 'الحالة',
  'duration': 'المدة',
  'sick_leave': 'إجازة مرضية',
  'annual_leave': 'إجازة سنوية',
  'emergency_leave': 'إجازة طارئة',
  'unpaid_leave': 'إجازة بدون راتب',
  'submit_request': 'إرسال الطلب',
  'cancel_request': 'إلغاء الطلب',
  'view_details': 'عرض التفاصيل',

  // صفحة الإعلانات
  'search_announcements': 'البحث في الإعلانات',
  'new': 'جديد',
  'no_announcements': 'لا توجد إعلانات',
  'announcement_details': 'تفاصيل الإعلان',
  'published_date': 'تاريخ النشر',
  'important': 'مهم',
  'mark_as_read': 'وضع كمقروء',
  'unread': 'غير مقروء',

  // صفحة كشوف المرتبات
  'payslips': 'كشوف المرتبات',
  'payslip': 'كشف المرتب',
  'payslip_details': 'تفاصيل كشف المرتب',
  'salary_summary': 'ملخص الراتب',
  'salary_breakdown': 'تفصيل الراتب',
  'basic_salary': 'الراتب الأساسي',
  'gross_salary': 'إجمالي الراتب',
  'net_salary': 'صافي الراتب',
  'allowances': 'البدلات',
  'deductions': 'الخصومات',
  'total_allowances': 'إجمالي البدلات',
  'total_deductions': 'إجمالي الخصومات',
  'housing_allowance': 'بدل السكن',
  'transportation_allowance': 'بدل المواصلات',
  'food_allowance': 'بدل الطعام',
  'phone_allowance': 'بدل الهاتف',
  'other_allowances': 'بدلات أخرى',
  'social_insurance': 'التأمينات الاجتماعية',
  'taxes': 'الضرائب',
  'loans': 'السلف',
  'absence_deduction': 'خصم الغياب',
  'other_deductions': 'خصومات أخرى',
  'total_received': 'إجمالي المستلم',
  'average_salary': 'متوسط الراتب',
  'last_payment': 'آخر دفعة',
  'payment_date': 'تاريخ الدفع',
  'working_days': 'أيام العمل',
  'period': 'الفترة',
  'bank': 'البنك',
  'account': 'الحساب',
  'notes': 'ملاحظات',
  'download': 'تحميل',
  'download_failed': 'فشل التحميل',
  'no_payslips': 'لا توجد كشوف مرتبات',
  'no_data': 'لا توجد بيانات',
  'paid': 'مدفوع',
  'under_review': 'قيد المراجعة',
  'draft': 'مسودة',
  'done': 'مكتمل',
  'verify': 'مراجعة',
  'cancel': 'ملغي',
  'egp': 'جنيه',

};

// Extension للسهولة في الاستخدام
extension LanguageExtension on BuildContext {
  LanguageManager get lang => LanguageManager();
  String translate(String key) => LanguageManager().translate(key);
  bool get isArabic => LanguageManager().isArabic;
}