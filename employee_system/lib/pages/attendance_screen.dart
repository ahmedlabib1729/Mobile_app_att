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

  // New location variables
  Position? currentPosition;
  String locationStatus = "Determining location...";
  bool isLocationEnabled = false;
  bool hasLocationPermission = false;

  @override
  void initState() {
    super.initState();
    currentTime = DateTime.now();

    print('Current time: ${DateTime.now()}');
    print('Timezone: ${DateTime.now().timeZoneName}');
    print('UTC offset: ${DateTime.now().timeZoneOffset}');

    timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        currentTime = DateTime.now();
        _updateWorkingHours();
      });
    });

    _loadAttendanceData();
    _checkLocationPermissions(); // Check location permissions
  }

  // New function to check location permissions
  Future<void> _checkLocationPermissions() async {
    try {
      // فحص إذا كانت خدمة الموقع مفعلة
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() {
          locationStatus = "خدمة الموقع غير مفعلة";
          isLocationEnabled = false;
        });

        // على iOS، اطلب من المستخدم تفعيل خدمة الموقع
        if (Theme.of(context).platform == TargetPlatform.iOS) {
          await Geolocator.openLocationSettings();
        }
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

          // عرض رسالة توضيحية للمستخدم
          _showLocationPermissionDialog();
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        setState(() {
          locationStatus = "صلاحية الموقع مرفوضة نهائياً";
          hasLocationPermission = false;
        });

        // توجيه المستخدم للإعدادات
        _showPermanentlyDeniedDialog();
        return;
      }

      // إذا كانت الصلاحيات موجودة
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

  // New function to get current location
  Future<void> _getCurrentLocation() async {
    try {
      setState(() {
        locationStatus = "Determining location...";
      });

      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 10),
      );

      setState(() {
        currentPosition = position;
        locationStatus = "Location determined";
      });
    } catch (e) {
      print('Error getting location: $e');
      setState(() {
        locationStatus = "Failed to determine location";
      });
    }
  }

  void _showLocationPermissionDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('صلاحية الموقع مطلوبة'),
        content: Text(
          'يحتاج التطبيق لصلاحية الوصول للموقع لتسجيل الحضور والانصراف. '
              'هذا يساعد في التحقق من تواجدك في موقع العمل.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _checkLocationPermissions(); // إعادة طلب الصلاحية
            },
            child: Text('السماح'),
          ),
        ],
      ),
    );
  }

  void _showPermanentlyDeniedDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('صلاحية الموقع مطلوبة'),
        content: Text(
          'تم رفض صلاحية الموقع نهائياً. '
              'يرجى الذهاب إلى إعدادات التطبيق والسماح بالوصول للموقع.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('لاحقاً'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              openAppSettings(); // فتح إعدادات التطبيق
            },
            child: Text('فتح الإعدادات'),
          ),
        ],
      ),
    );
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
          // Assume server time is UTC
          String checkInString = attendanceStatus['check_in'];

          // Parse datetime
          DateTime parsedTime;
          if (checkInString.contains('T') || checkInString.contains('Z')) {
            // If ISO format
            parsedTime = DateTime.parse(checkInString);
          } else {
            // If normal Odoo format (2025-06-06 18:29:22)
            parsedTime = DateTime.parse(checkInString);
            // Treat as UTC
            parsedTime = DateTime.utc(
              parsedTime.year,
              parsedTime.month,
              parsedTime.day,
              parsedTime.hour,
              parsedTime.minute,
              parsedTime.second,
            );
          }

          // Convert to local time (e.g. add 4 hours for UAE)
          checkInTime = parsedTime.toLocal();

          print('Server time: $checkInString');
          print('Parsed time: $parsedTime');
          print('Local time: $checkInTime');

          _updateWorkingHours();
        } else {
          workingHours = "0:00";
          checkInTime = null;
        }
      });

      // Fetch attendance history
      try {
        final records = await widget.odooService.getAttendanceHistory(widget.employee.id);
        setState(() {
          attendanceRecords = records;
        });
      } catch (e) {
        print('Error fetching attendance history: $e');
        // Continue if history fails
        setState(() {
          attendanceRecords = [];
        });
      }

      setState(() {
        isLoading = false;
      });
    } catch (e) {
      print('Error loading attendance data: $e');
      setState(() {
        isLoading = false;
        isCheckedIn = false;
        checkInTime = null;
        workingHours = "0:00";
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Attendance data loading error'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _toggleAttendance() async {
    try {
      // Check location before toggling attendance
      if (!hasLocationPermission || !isLocationEnabled) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Location service and permissions must be enabled'),
            backgroundColor: Colors.orange,
            action: SnackBarAction(
              label: 'Open Settings',
              onPressed: () {
                openAppSettings();
              },
            ),
          ),
        );
        return;
      }

      // Get current location
      await _getCurrentLocation();

      if (currentPosition == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Location not determined, try again'),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }

      setState(() {
        isLoading = true;
      });

      if (isCheckedIn) {
        // Check out with location
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
              content: Text('Check-out successful'),
              backgroundColor: Colors.green,
            ),
          );
          _loadAttendanceData();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? 'Check-out failed'),
              backgroundColor: Colors.red,
            ),
          );
        }
      } else {
        // Check in with location
        final result = await widget.odooService.checkInWithLocation(
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
              content: Text('Check-in successful'),
              backgroundColor: Colors.green,
            ),
          );
          _loadAttendanceData();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? 'Check-in failed'),
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
          content: Text('Error occurred: $e'),
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
            'Attendance',
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
          _buildInfoCard('Working Hours', workingHours, mainBlue),
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
            DateFormat('EEEE, d MMMM yyyy', 'en').format(currentTime),
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

          // Show new location status
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
                  isCheckedIn ? 'You are checked in' : 'You are not checked in yet',
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
                'Check-in time: ${DateFormat('hh:mm a').format(checkInTime!)}',
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
                isCheckedIn ? 'Check Out' : 'Check In',
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

  // New widget to show location status
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
            'Attendance Records',
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
                'No attendance records',
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
                    'Duration: ${record['duration'] ?? 'N/A'}',
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
                    'In',
                    record['checkIn'] ?? '',
                    mainBlue,
                  ),
                  const SizedBox(height: 4),
                  _buildTimeChip(
                    'Out',
                    record['checkOut'] ?? 'N/A',
                    (record['checkOut'] != null && record['checkOut'] != 'N/A')
                        ? accentViolet
                        : Colors.grey,
                  ),
                ],
              ),
            ],
          ),
          // Show location if available
          if (record['check_in_location'] != null || record['check_out_location'] != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                if (record['check_in_location'] != null) ...[
                  Icon(Icons.location_on, size: 16, color: Colors.green),
                  const SizedBox(width: 4),
                  Text(
                    'In: ${record['check_in_location']}',
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
                    'Out: ${record['check_out_location']}',
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
