// pages/calendar_screen.dart
import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:intl/intl.dart';
import '../models/appointment.dart';
import '../services/appointment_service.dart';
import 'add_appointment_screen.dart';
import 'appointment_details_screen.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({Key? key}) : super(key: key);

  @override
  _CalendarScreenState createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  late final ValueNotifier<List<Appointment>> _selectedAppointments;
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  Map<DateTime, List<Appointment>> _appointments = {};

  @override
  void initState() {
    super.initState();
    _selectedDay = DateTime.now();
    _selectedAppointments = ValueNotifier([]);
    _loadAppointments();
  }

  @override
  void dispose() {
    _selectedAppointments.dispose();
    super.dispose();
  }

  Future<void> _loadAppointments() async {
    final appointments = await AppointmentService.getAppointments();
    final Map<DateTime, List<Appointment>> appointmentMap = {};

    for (final appointment in appointments) {
      final date = DateTime(
        appointment.dateTime.year,
        appointment.dateTime.month,
        appointment.dateTime.day,
      );

      if (appointmentMap[date] == null) {
        appointmentMap[date] = [];
      }
      appointmentMap[date]!.add(appointment);
    }

    setState(() {
      _appointments = appointmentMap;
    });

    if (_selectedDay != null) {
      _selectedAppointments.value = _getAppointmentsForDay(_selectedDay!);
    }
  }

  List<Appointment> _getAppointmentsForDay(DateTime day) {
    final normalizedDay = DateTime(day.year, day.month, day.day);
    return _appointments[normalizedDay] ?? [];
  }

  void _onDaySelected(DateTime selectedDay, DateTime focusedDay) {
    if (!isSameDay(_selectedDay, selectedDay)) {
      setState(() {
        _selectedDay = selectedDay;
        _focusedDay = focusedDay;
      });
      _selectedAppointments.value = _getAppointmentsForDay(selectedDay);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('التقويم'),
        centerTitle: true,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.today),
            onPressed: () {
              setState(() {
                _focusedDay = DateTime.now();
                _selectedDay = DateTime.now();
              });
              _selectedAppointments.value = _getAppointmentsForDay(DateTime.now());
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // التقويم
          TableCalendar<Appointment>(
            firstDay: DateTime.utc(2020, 1, 1),
            lastDay: DateTime.utc(2030, 12, 31),
            focusedDay: _focusedDay,
            calendarFormat: _calendarFormat,
            selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
            eventLoader: _getAppointmentsForDay,
            startingDayOfWeek: StartingDayOfWeek.saturday,
            availableCalendarFormats: const {
              CalendarFormat.month: 'شهر',
              CalendarFormat.twoWeeks: 'أسبوعين',
              CalendarFormat.week: 'أسبوع',
            },
            calendarStyle: CalendarStyle(
              outsideDaysVisible: false,
              selectedDecoration: BoxDecoration(
                color: Theme.of(context).primaryColor,
                shape: BoxShape.circle,
              ),
              todayDecoration: BoxDecoration(
                color: Theme.of(context).primaryColor.withOpacity(0.5),
                shape: BoxShape.circle,
              ),
              markerDecoration: BoxDecoration(
                color: Theme.of(context).colorScheme.secondary,
                shape: BoxShape.circle,
              ),
              markersMaxCount: 3,
              markersAutoAligned: true,
            ),
            headerStyle: const HeaderStyle(
              formatButtonVisible: true,
              titleCentered: true,
              formatButtonShowsNext: false,
              formatButtonTextStyle: TextStyle(
                fontSize: 14,
                color: Colors.white,
              ),
              formatButtonDecoration: BoxDecoration(
                color: Colors.blue,
                borderRadius: BorderRadius.all(Radius.circular(12)),
              ),
            ),
            onDaySelected: _onDaySelected,
            onFormatChanged: (format) {
              if (_calendarFormat != format) {
                setState(() {
                  _calendarFormat = format;
                });
              }
            },
            onPageChanged: (focusedDay) {
              _focusedDay = focusedDay;
            },
            calendarBuilders: CalendarBuilders(
              markerBuilder: (context, day, appointments) {
                if (appointments.isEmpty) return const SizedBox();

                return Positioned(
                  bottom: 1,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: appointments.take(3).map((appointment) {
                      final colors = AppointmentService.getAppointmentColors();
                      return Container(
                        margin: const EdgeInsets.symmetric(horizontal: 1),
                        height: 6,
                        width: 6,
                        decoration: BoxDecoration(
                          color: Color(colors[appointment.colorIndex]),
                          shape: BoxShape.circle,
                        ),
                      );
                    }).toList(),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 8),
          // قائمة المواعيد لليوم المحدد
          Expanded(
            child: ValueListenableBuilder<List<Appointment>>(
              valueListenable: _selectedAppointments,
              builder: (context, appointments, _) {
                if (appointments.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.event_available,
                          size: 64,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'لا توجد مواعيد في هذا اليوم',
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: appointments.length,
                  padding: const EdgeInsets.all(16),
                  itemBuilder: (context, index) {
                    final appointment = appointments[index];
                    final colors = AppointmentService.getAppointmentColors();
                    final color = Color(colors[appointment.colorIndex]);

                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      elevation: 2,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(
                          color: appointment.isCompleted
                              ? Colors.grey[300]!
                              : color.withOpacity(0.3),
                          width: 1,
                        ),
                      ),
                      child: InkWell(
                        onTap: () async {
                          await Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => AppointmentDetailsScreen(
                                appointment: appointment,
                              ),
                            ),
                          );
                          _loadAppointments();
                        },
                        borderRadius: BorderRadius.circular(12),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Row(
                            children: [
                              Container(
                                width: 4,
                                height: 60,
                                decoration: BoxDecoration(
                                  color: appointment.isCompleted
                                      ? Colors.grey[400]
                                      : color,
                                  borderRadius: BorderRadius.circular(2),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      appointment.title,
                                      style: TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                        decoration: appointment.isCompleted
                                            ? TextDecoration.lineThrough
                                            : null,
                                        color: appointment.isCompleted
                                            ? Colors.grey[600]
                                            : null,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      DateFormat('hh:mm a').format(appointment.dateTime),
                                      style: TextStyle(
                                        fontSize: 14,
                                        color: Colors.grey[600],
                                      ),
                                    ),
                                    if (appointment.location != null) ...[
                                      const SizedBox(height: 4),
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.location_on,
                                            size: 16,
                                            color: Colors.grey[600],
                                          ),
                                          const SizedBox(width: 4),
                                          Expanded(
                                            child: Text(
                                              appointment.location!,
                                              style: TextStyle(
                                                fontSize: 12,
                                                color: Colors.grey[600],
                                              ),
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                              if (appointment.isCompleted)
                                Icon(
                                  Icons.check_circle,
                                  color: Colors.green[600],
                                  size: 24,
                                )
                              else if (appointment.isNotificationEnabled)
                                Icon(
                                  Icons.notifications_active,
                                  color: Colors.grey[600],
                                  size: 20,
                                ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => AddAppointmentScreen(
                selectedDate: _selectedDay,
              ),
            ),
          );
          _loadAppointments();
        },
        child: const Icon(Icons.add),
        tooltip: 'إضافة موعد',
      ),
    );
  }
}