// pages/appointment_details_screen.dart
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/appointment.dart';
import '../services/appointment_service.dart';
import 'add_appointment_screen.dart';

class AppointmentDetailsScreen extends StatefulWidget {
  final Appointment appointment;

  const AppointmentDetailsScreen({
    Key? key,
    required this.appointment,
  }) : super(key: key);

  @override
  _AppointmentDetailsScreenState createState() => _AppointmentDetailsScreenState();
}

class _AppointmentDetailsScreenState extends State<AppointmentDetailsScreen> {
  late Appointment _appointment;

  @override
  void initState() {
    super.initState();
    _appointment = widget.appointment;
  }

  String _getNotificationText(int minutes) {
    if (minutes < 60) {
      return '$minutes دقيقة';
    } else if (minutes == 60) {
      return 'ساعة واحدة';
    } else if (minutes == 120) {
      return 'ساعتين';
    } else if (minutes == 1440) {
      return 'يوم واحد';
    } else {
      return '${minutes ~/ 60} ساعات';
    }
  }

  Future<void> _toggleCompleted() async {
    setState(() {
      _appointment = _appointment.copyWith(isCompleted: !_appointment.isCompleted);
    });
    await AppointmentService.updateAppointment(_appointment);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          _appointment.isCompleted
              ? 'تم تحديد الموعد كمكتمل'
              : 'تم إلغاء تحديد الموعد كمكتمل',
        ),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Future<void> _deleteAppointment() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('حذف الموعد'),
        content: const Text('هل أنت متأكد من حذف هذا الموعد؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await AppointmentService.deleteAppointment(_appointment.id);
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppointmentService.getAppointmentColors();
    final color = Color(colors[_appointment.colorIndex]);
    final dateFormat = DateFormat('EEEE, d MMMM yyyy', 'ar');
    final timeFormat = DateFormat('hh:mm a');

    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        title: const Text('تفاصيل الموعد'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () async {
              final result = await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => AddAppointmentScreen(
                    appointmentToEdit: _appointment,
                  ),
                ),
              );

              if (result != null) {
                Navigator.pop(context);
              }
            },
          ),
          IconButton(
            icon: const Icon(Icons.delete),
            onPressed: _deleteAppointment,
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // رأس الصفحة مع اللون
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: _appointment.isCompleted ? Colors.grey[400] : color,
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(32),
                  bottomRight: Radius.circular(32),
                ),
              ),
              child: Column(
                children: [
                  Icon(
                    _appointment.isCompleted
                        ? Icons.check_circle
                        : Icons.event,
                    size: 48,
                    color: Colors.white,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _appointment.title,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _appointment.isCompleted ? 'مكتمل' : 'نشط',
                    style: const TextStyle(
                      fontSize: 16,
                      color: Colors.white70,
                    ),
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // التاريخ والوقت
                  Card(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          ListTile(
                            leading: Icon(
                              Icons.calendar_today,
                              color: color,
                            ),
                            title: const Text('التاريخ'),
                            subtitle: Text(
                              dateFormat.format(_appointment.dateTime),
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                          const Divider(),
                          ListTile(
                            leading: Icon(
                              Icons.access_time,
                              color: color,
                            ),
                            title: const Text('الوقت'),
                            subtitle: Text(
                              timeFormat.format(_appointment.dateTime),
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                          if (_appointment.location != null) ...[
                            const Divider(),
                            ListTile(
                              leading: Icon(
                                Icons.location_on,
                                color: color,
                              ),
                              title: const Text('المكان'),
                              subtitle: Text(
                                _appointment.location!,
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // الوصف
                  Card(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.description,
                                color: color,
                              ),
                              const SizedBox(width: 8),
                              const Text(
                                'الوصف',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _appointment.description,
                            style: const TextStyle(
                              fontSize: 16,
                              height: 1.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // الإشعارات
                  Card(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: ListTile(
                        leading: Icon(
                          _appointment.isNotificationEnabled
                              ? Icons.notifications_active
                              : Icons.notifications_off,
                          color: _appointment.isNotificationEnabled
                              ? color
                              : Colors.grey,
                        ),
                        title: const Text('الإشعارات'),
                        subtitle: Text(
                          _appointment.isNotificationEnabled
                              ? 'التنبيه قبل الموعد بـ ${_getNotificationText(_appointment.notificationMinutesBefore)}'
                              : 'الإشعارات مغلقة',
                          style: const TextStyle(
                            fontSize: 16,
                          ),
                        ),
                      ),
                    ),
                  ),

                  // الملاحظات
                  if (_appointment.notes != null && _appointment.notes!.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  Icons.note,
                                  color: color,
                                ),
                                const SizedBox(width: 8),
                                const Text(
                                  'ملاحظات',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Text(
                              _appointment.notes!,
                              style: const TextStyle(
                                fontSize: 16,
                                height: 1.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],

                  const SizedBox(height: 32),

                  // زر تحديد كمكتمل
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _toggleCompleted,
                      icon: Icon(
                        _appointment.isCompleted
                            ? Icons.replay
                            : Icons.check_circle,
                      ),
                      label: Text(
                        _appointment.isCompleted
                            ? 'إلغاء التحديد كمكتمل'
                            : 'تحديد كمكتمل',
                        style: const TextStyle(fontSize: 16),
                      ),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.all(16),
                        backgroundColor: _appointment.isCompleted
                            ? Colors.orange
                            : Colors.green,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}