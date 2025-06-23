// services/appointment_service.dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz;
import '../models/appointment.dart';

class AppointmentService {
  static const String _storageKey = 'appointments';
  static final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();

  // تهيئة خدمة الإشعارات
  static Future<void> initializeNotifications() async {
    tz.initializeTimeZones();

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _notifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        // معالجة الضغط على الإشعار
        print('Notification clicked: ${response.payload}');
      },
    );

    // طلب أذونات الإشعارات
    await _requestNotificationPermissions();
  }

  static Future<void> _requestNotificationPermissions() async {
    await _notifications.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>()?.requestNotificationsPermission();
  }

  // حفظ موعد جديد
  static Future<void> saveAppointment(Appointment appointment) async {
    final prefs = await SharedPreferences.getInstance();
    final appointments = await getAppointments();

    // إضافة الموعد الجديد
    appointments.add(appointment);

    // حفظ في التخزين المحلي
    final jsonList = appointments.map((a) => a.toJson()).toList();
    await prefs.setString(_storageKey, jsonEncode(jsonList));

    // جدولة الإشعار إذا كان مفعلاً
    if (appointment.isNotificationEnabled) {
      await _scheduleNotification(appointment);
    }
  }

  // تحديث موعد موجود
  static Future<void> updateAppointment(Appointment appointment) async {
    final prefs = await SharedPreferences.getInstance();
    final appointments = await getAppointments();

    // البحث عن الموعد وتحديثه
    final index = appointments.indexWhere((a) => a.id == appointment.id);
    if (index != -1) {
      appointments[index] = appointment;

      // حفظ التحديثات
      final jsonList = appointments.map((a) => a.toJson()).toList();
      await prefs.setString(_storageKey, jsonEncode(jsonList));

      // إلغاء الإشعار القديم وجدولة واحد جديد
      await _cancelNotification(int.parse(appointment.id));
      if (appointment.isNotificationEnabled) {
        await _scheduleNotification(appointment);
      }
    }
  }

  // حذف موعد
  static Future<void> deleteAppointment(String appointmentId) async {
    final prefs = await SharedPreferences.getInstance();
    final appointments = await getAppointments();

    // حذف الموعد
    appointments.removeWhere((a) => a.id == appointmentId);

    // حفظ التحديثات
    final jsonList = appointments.map((a) => a.toJson()).toList();
    await prefs.setString(_storageKey, jsonEncode(jsonList));

    // إلغاء الإشعار
    await _cancelNotification(int.parse(appointmentId));
  }

  // الحصول على جميع المواعيد
  static Future<List<Appointment>> getAppointments() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_storageKey);

    if (jsonString == null) return [];

    final jsonList = jsonDecode(jsonString) as List;
    return jsonList.map((json) => Appointment.fromJson(json)).toList();
  }

  // الحصول على مواعيد يوم معين
  static Future<List<Appointment>> getAppointmentsByDate(DateTime date) async {
    final appointments = await getAppointments();
    return appointments.where((a) {
      return a.dateTime.year == date.year &&
          a.dateTime.month == date.month &&
          a.dateTime.day == date.day;
    }).toList();
  }

  // الحصول على المواعيد القادمة
  static Future<List<Appointment>> getUpcomingAppointments() async {
    final appointments = await getAppointments();
    final now = DateTime.now();
    return appointments
        .where((a) => a.dateTime.isAfter(now) && !a.isCompleted)
        .toList()
      ..sort((a, b) => a.dateTime.compareTo(b.dateTime));
  }

  // جدولة إشعار لموعد
  static Future<void> _scheduleNotification(Appointment appointment) async {
    final scheduledDate = appointment.dateTime.subtract(
      Duration(minutes: appointment.notificationMinutesBefore),
    );

    // التحقق من أن الوقت في المستقبل
    if (scheduledDate.isBefore(DateTime.now())) return;

    const androidDetails = AndroidNotificationDetails(
      'appointments_channel',
      'مواعيد العمل',
      channelDescription: 'إشعارات المواعيد',
      importance: Importance.high,
      priority: Priority.high,
      playSound: true,
      enableVibration: true,
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.zonedSchedule(
      int.parse(appointment.id),
      appointment.title,
      'الموعد بعد ${appointment.notificationMinutesBefore} دقيقة${appointment.location != null ? " في ${appointment.location}" : ""}',
      tz.TZDateTime.from(scheduledDate, tz.local),
      details,
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
      payload: appointment.id,
    );
  }

  // إلغاء إشعار
  static Future<void> _cancelNotification(int id) async {
    await _notifications.cancel(id);
  }

  // تحديد موعد كمكتمل
  static Future<void> markAsCompleted(String appointmentId) async {
    final appointments = await getAppointments();
    final index = appointments.indexWhere((a) => a.id == appointmentId);

    if (index != -1) {
      final updatedAppointment = appointments[index].copyWith(isCompleted: true);
      await updateAppointment(updatedAppointment);
    }
  }

  // الحصول على ألوان المواعيد
  static List<int> getAppointmentColors() {
    return [
      0xFF2196F3, // أزرق
      0xFF4CAF50, // أخضر
      0xFFFF9800, // برتقالي
      0xFFE91E63, // وردي
      0xFF9C27B0, // بنفسجي
      0xFF00BCD4, // سماوي
      0xFFFFEB3B, // أصفر
      0xFF795548, // بني
    ];
  }
}