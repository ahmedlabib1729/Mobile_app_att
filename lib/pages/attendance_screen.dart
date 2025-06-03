import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'dart:async';
import '../services/odoo_service.dart';
import '../models/employee.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

class AttendanceScreen extends StatefulWidget {
  final OdooService odooService;
  final Employee employee;

  const AttendanceScreen({
    Key? key,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _AttendanceScreenState createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  bool isCheckedIn = false;
  DateTime? checkInTime;
  String workingHours = "0:00";
  int requestCount = 0;

  List<Map<String, dynamic>> attendanceRecords = [];

  late DateTime currentTime;
  late Timer timer;
  bool isLoading = true;

  // متغيرات الموقع الجديدة
  Position? currentPosition;
  String locationStatus = "جاري تحديد الموقع...";
  bool isLocationEnabled = false;
  bool hasLocationPermission = false;

  @override
  void initState() {
    super.initState();
    currentTime = DateTime.now();

    timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        currentTime = DateTime.now();
        _updateWorkingHours();
      });
    });

    _loadAttendanceData();
    _checkLocationPermissions(); // فحص صلاحيات الموقع
  }

  // دالة جديدة لفحص صلاحيات الموقع
  Future<void> _checkLocationPermissions() async {
    try {
      // فحص إذا كانت خدمة الموقع مفعلة
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() {
          locationStatus = "خدمة الموقع غير مفعلة";
          isLocationEnabled = false;
        });
        return;
      }

      // فحص الصلاحيات
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          setState(() {
            locationStatus = "صلاحية الموقع مرفوضة";
            hasLocationPermission = false;
          });
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        setState(() {
          locationStatus = "صلاحية الموقع مرفوضة نهائياً";
          hasLocationPermission = false;
        });
        return;
      }

      // إذا كانت الصلاحيات موجودة، احصل على الموقع
      setState(() {
        isLocationEnabled = true;
        hasLocationPermission = true;
      });

      await _getCurrentLocation();
    } catch (e) {
      print('خطأ في فحص صلاحيات الموقع: $e');
      setState(() {
        locationStatus = "خطأ في تحديد الموقع";
      });
    }
  }

  // دالة جديدة للحصول على الموقع الحالي
  Future<void> _getCurrentLocation() async {
    try {
      setState(() {
        locationStatus = "جاري تحديد الموقع...";
      });

      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 10),
      );

      setState(() {
        currentPosition = position;
        locationStatus = "تم تحديد الموقع";
      });
    } catch (e) {
      print('خطأ في الحصول على الموقع: $e');
      setState(() {
        locationStatus = "فشل تحديد الموقع";
      });
    }
  }

  void _updateWorkingHours() {
    if (isCheckedIn && checkInTime != null) {
      Duration workDuration = currentTime.difference(checkInTime!);
      int hours = workDuration.inHours;
      int minutes = (workDuration.inMinutes % 60);
      workingHours = "$hours:${minutes.toString().padLeft(2, '0')}";
    }
  }

  @override
  void dispose() {
    timer.cancel();
    super.dispose();
  }

  Future<void> _loadAttendanceData() async {
    try {
      setState(() {
        isLoading = true;
      });

      final attendanceStatus = await widget.odooService.getCurrentAttendanceStatus(widget.employee.id);

      setState(() {
        isCheckedIn = attendanceStatus['is_checked_in'] ?? false;
        if (isCheckedIn && attendanceStatus['check_in'] != null) {
          checkInTime = DateTime.parse(attendanceStatus['check_in']);
          _updateWorkingHours();
        }
      });

      final records = await widget.odooService.getAttendanceHistory(widget.employee.id);

      setState(() {
        attendanceRecords = records;
        isLoading = false;
      });
    } catch (e) {
      print('Error loading attendance data: $e');
      setState(() {
        isLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to load attendance data: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _toggleAttendance() async {
    try {
      // التحقق من الموقع قبل تسجيل الحضور/الانصراف
      if (!hasLocationPermission || !isLocationEnabled) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('يجب تفعيل خدمة الموقع والسماح بالصلاحيات'),
            backgroundColor: Colors.orange,
            action: SnackBarAction(
              label: 'فتح الإعدادات',
              onPressed: () {
                openAppSettings();
              },
            ),
          ),
        );
        return;
      }

      // الحصول على الموقع الحالي
      await _getCurrentLocation();

      if (currentPosition == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('لم يتم تحديد الموقع، حاول مرة أخرى'),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }

      setState(() {
        isLoading = true;
      });

      if (isCheckedIn) {
        // Check out مع إرسال الموقع
        final result = await widget.odooService.checkOutWithLocation(
          widget.employee.id,
          currentPosition!.latitude,
          currentPosition!.longitude,
        );

        if (result['success']) {
          setState(() {
            isCheckedIn = false;
            checkInTime = null;
            workingHours = "0:00";
          });

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('تم تسجيل الانصراف بنجاح'),
              backgroundColor: Colors.green,
            ),
          );
          _loadAttendanceData();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? 'فشل تسجيل الانصراف'),
              backgroundColor: Colors.red,
            ),
          );
        }
      } else {
        // Check in مع إرسال الموقع
        final result = await widget.odooService.checkInWithLocation(
          widget.employee.id,
          currentPosition!.latitude,
          currentPosition!.longitude,
        );

        if (result['success']) {
          setState(() {
            isCheckedIn = true;
            checkInTime = DateTime.now();
          });

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('تم تسجيل الحضور بنجاح'),
              backgroundColor: Colors.green,
            ),
          );
          _loadAttendanceData();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? 'فشل تسجيل الحضور'),
              backgroundColor: Colors.red,
              duration: Duration(seconds: 5),
            ),
          );
        }
      }
    } catch (e) {
      print('Error toggling attendance: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('حدث خطأ: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    const Color mainBlue = Color(0xFF4F8CFF);
    const Color accentViolet = Color(0xFFB568FF);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFFE0EAFC),
              Color(0xFFCFDEF3),
              Color(0xFFF5F5FF),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: isLoading
            ? const Center(child: CircularProgressIndicator())
            : SafeArea(
          child: Column(
            children: [
              _buildAppBar(mainBlue),
              _buildSummarySection(mainBlue),
              Expanded(
                child: _buildMainContent(mainBlue, accentViolet),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Modern AppBar
  Widget _buildAppBar(Color mainBlue) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.93),
        boxShadow: [
          BoxShadow(
            color: mainBlue.withOpacity(0.06),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
        border: const Border(
          bottom: BorderSide(color: Color(0xFFE0EAFC), width: 1),
        ),
      ),
      child: Row(
        children: [
          IconButton(
            icon: Icon(Icons.arrow_back_ios, color: mainBlue),
            onPressed: () => Navigator.of(context).pop(),
          ),
          const Spacer(),
          const Text(
            'الحضور والانصراف',
            style: TextStyle(
              fontSize: 20,
              color: Color(0xFF222B45),
              fontWeight: FontWeight.bold,
              letterSpacing: 0.8,
            ),
          ),
          const Spacer(),
          IconButton(
            icon: Icon(Icons.refresh, color: mainBlue),
            onPressed: _loadAttendanceData,
          ),
        ],
      ),
    );
  }

  // Glass summary cards
  Widget _buildSummarySection(Color mainBlue) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 15, horizontal: 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildInfoCard('ساعات العمل', workingHours, mainBlue),
        ],
      ),
    );
  }

  Widget _buildInfoCard(String title, String value, Color color) {
    return Container(
      width: 145,
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.09),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: color.withOpacity(0.14),
          width: 1.1,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.07),
            blurRadius: 13,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 13,
              color: color.withOpacity(0.80),
              fontWeight: FontWeight.w500,
              letterSpacing: 0.4,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMainContent(Color mainBlue, Color accentViolet) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
      child: Column(
        children: [
          // Current date
          Text(
            DateFormat('EEEE, d MMMM yyyy', 'ar').format(currentTime),
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w600,
              color: mainBlue.withOpacity(0.8),
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 10),
          // Current time
          Text(
            DateFormat('hh:mm a').format(currentTime),
            style: const TextStyle(
              fontSize: 40,
              fontWeight: FontWeight.bold,
              color: Color(0xFF222B45),
            ),
          ),
          const SizedBox(height: 22),

          // عرض حالة الموقع الجديدة
          _buildLocationStatus(mainBlue),
          const SizedBox(height: 16),

          // Status message
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
            decoration: BoxDecoration(
              color: isCheckedIn
                  ? Colors.green.withOpacity(0.09)
                  : Colors.redAccent.withOpacity(0.09),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isCheckedIn
                    ? Colors.green.withOpacity(0.14)
                    : Colors.redAccent.withOpacity(0.12),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  isCheckedIn ? Icons.check_circle : Icons.cancel,
                  color: isCheckedIn ? Colors.green : Colors.redAccent,
                  size: 22,
                ),
                const SizedBox(width: 8),
                Text(
                  isCheckedIn ? 'أنت مسجل حضور' : 'لم تسجل حضورك بعد',
                  style: TextStyle(
                    fontSize: 16,
                    color: isCheckedIn ? Colors.green : Colors.redAccent,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          // Check-in time if available
          if (isCheckedIn && checkInTime != null)
            Padding(
              padding: const EdgeInsets.only(top: 8.0),
              child: Text(
                'وقت الحضور: ${DateFormat('hh:mm a').format(checkInTime!)}',
                style: TextStyle(
                  fontSize: 13,
                  color: mainBlue.withOpacity(0.80),
                ),
              ),
            ),
          const SizedBox(height: 30),

          // Check-in/out Button
          Container(
            width: double.infinity,
            height: 54,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: isCheckedIn
                    ? [Colors.redAccent, Colors.red.shade300]
                    : [mainBlue, accentViolet],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: mainBlue.withOpacity(0.12),
                  blurRadius: 13,
                  offset: const Offset(0, 7),
                ),
              ],
            ),
            child: ElevatedButton(
              onPressed: isLoading ? null : _toggleAttendance,
              style: ElevatedButton.styleFrom(
                elevation: 0,
                backgroundColor: Colors.transparent,
                foregroundColor: Colors.white,
                shadowColor: Colors.transparent,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                padding: EdgeInsets.zero,
              ),
              child: isLoading
                  ? const SizedBox(
                width: 26,
                height: 26,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
                  : Text(
                isCheckedIn ? 'تسجيل انصراف' : 'تسجيل حضور',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2,
                ),
              ),
            ),
          ),
          const SizedBox(height: 28),

          // Attendance history
          _buildAttendanceHistory(mainBlue, accentViolet),
        ],
      ),
    );
  }

  // ويدجت جديد لعرض حالة الموقع
  Widget _buildLocationStatus(Color mainBlue) {
    IconData icon;
    Color statusColor;

    if (!isLocationEnabled || !hasLocationPermission) {
      icon = Icons.location_off;
      statusColor = Colors.red;
    } else if (currentPosition != null) {
      icon = Icons.location_on;
      statusColor = Colors.green;
    } else {
      icon = Icons.location_searching;
      statusColor = Colors.orange;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: statusColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            color: statusColor,
            size: 20,
          ),
          const SizedBox(width: 8),
          Text(
            locationStatus,
            style: TextStyle(
              fontSize: 14,
              color: statusColor,
              fontWeight: FontWeight.w500,
            ),
          ),
          if (currentPosition != null) ...[
            const SizedBox(width: 8),
            Text(
              '(${currentPosition!.latitude.toStringAsFixed(4)}, ${currentPosition!.longitude.toStringAsFixed(4)})',
              style: TextStyle(
                fontSize: 12,
                color: statusColor.withOpacity(0.8),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAttendanceHistory(Color mainBlue, Color accentViolet) {
    return Container(
      alignment: Alignment.centerLeft,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'سجل الحضور',
            style: TextStyle(
              fontSize: 19,
              fontWeight: FontWeight.bold,
              color: Color(0xFF222B45),
            ),
          ),
          const SizedBox(height: 14),
          attendanceRecords.isEmpty
              ? Center(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Text(
                'لا توجد سجلات حضور',
                style: TextStyle(
                  color: Colors.grey,
                  fontSize: 15.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          )
              : Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.98),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: mainBlue.withOpacity(0.07),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: attendanceRecords.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final record = attendanceRecords[index];
                return _buildRecordItem(record, mainBlue, accentViolet);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRecordItem(Map<String, dynamic> record, Color mainBlue, Color accentViolet) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // Date
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    record['date'] ?? '',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: Color(0xFF222B45),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'المدة: ${record['duration'] ?? 'N/A'}',
                    style: TextStyle(
                      color: mainBlue.withOpacity(0.73),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const Spacer(),

              // Check-in/out times
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _buildTimeChip(
                    'دخول',
                    record['checkIn'] ?? '',
                    mainBlue,
                  ),
                  const SizedBox(height: 4),
                  _buildTimeChip(
                    'خروج',
                    record['checkOut'] ?? 'N/A',
                    (record['checkOut'] != null && record['checkOut'] != 'N/A')
                        ? accentViolet
                        : Colors.grey,
                  ),
                ],
              ),
            ],
          ),
          // عرض الموقع إذا كان متاحاً
          if (record['check_in_location'] != null || record['check_out_location'] != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                if (record['check_in_location'] != null) ...[
                  Icon(Icons.location_on, size: 16, color: Colors.green),
                  const SizedBox(width: 4),
                  Text(
                    'دخول: ${record['check_in_location']}',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
                if (record['check_out_location'] != null) ...[
                  const SizedBox(width: 16),
                  Icon(Icons.location_on, size: 16, color: Colors.red),
                  const SizedBox(width: 4),
                  Text(
                    'خروج: ${record['check_out_location']}',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTimeChip(String label, String time, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.13),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.29)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 11,
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
          Text(
            time,
            style: TextStyle(
              fontSize: 11,
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}