import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'dart:async';
import '../services/odoo_service.dart';
import '../models/employee.dart';

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
  // متغيرات لتتبع حالة الحضور
  bool isCheckedIn = false;
  DateTime? checkInTime;
  String workingHours = "0:00";
  int requestCount = 0;

  // متغيرات لسجل الحضور
  List<Map<String, dynamic>> attendanceRecords = [];

  // متغيرات للوقت الحالي
  late DateTime currentTime;
  late Timer timer;

  // حالة التحميل
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    currentTime = DateTime.now();

    // تحديث الوقت كل ثانية
    timer = Timer.periodic(Duration(seconds: 1), (timer) {
      setState(() {
        currentTime = DateTime.now();
        _updateWorkingHours();
      });
    });

    // تحميل بيانات الحضور
    _loadAttendanceData();
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

  // تحميل بيانات الحضور من Odoo
  Future<void> _loadAttendanceData() async {
    try {
      setState(() {
        isLoading = true;
      });

      // جلب حالة الحضور الحالية للموظف
      final attendanceStatus = await widget.odooService.getCurrentAttendanceStatus(widget.employee.id);

      setState(() {
        isCheckedIn = attendanceStatus['is_checked_in'] ?? false;

        // إذا كان مسجل حضور، أخذ وقت الحضور
        if (isCheckedIn && attendanceStatus['check_in'] != null) {
          checkInTime = DateTime.parse(attendanceStatus['check_in']);
          _updateWorkingHours();
        }
      });

      // جلب سجل الحضور السابق
      final records = await widget.odooService.getAttendanceHistory(widget.employee.id);

      setState(() {
        attendanceRecords = records;
        isLoading = false;
      });
    } catch (e) {
      print('خطأ في تحميل بيانات الحضور: $e');
      setState(() {
        isLoading = false;
      });

      // عرض رسالة خطأ
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('فشل في تحميل بيانات الحضور: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  // تسجيل الحضور أو الانصراف
  Future<void> _toggleAttendance() async {
    try {
      setState(() {
        isLoading = true;
      });

      if (isCheckedIn) {
        // تسجيل انصراف
        final result = await widget.odooService.checkOut(widget.employee.id);

        if (result['success']) {
          setState(() {
            isCheckedIn = false;
            checkInTime = null;
            workingHours = "0:00";
          });

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('تم تسجيل الانصراف بنجاح'),
              backgroundColor: Colors.green,
            ),
          );

          // تحديث سجل الحضور
          _loadAttendanceData();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? 'فشل في تسجيل الانصراف'),
              backgroundColor: Colors.red,
            ),
          );
        }
      } else {
        // تسجيل حضور
        final result = await widget.odooService.checkIn(widget.employee.id);

        if (result['success']) {
          setState(() {
            isCheckedIn = true;
            checkInTime = DateTime.now();
          });

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('تم تسجيل الحضور بنجاح'),
              backgroundColor: Colors.green,
            ),
          );

          // تحديث البيانات
          _loadAttendanceData();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? 'فشل في تسجيل الحضور'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      print('خطأ في تسجيل الحضور/الانصراف: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('فشل في تسجيل الحضور/الانصراف: $e'),
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
    return Scaffold(
      backgroundColor: Color(0xFFF5F5F5),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : SafeArea(
        child: Column(
          children: [
            _buildAppBar(),
            _buildSummarySection(),
            Expanded(
              child: _buildMainContent(),
            ),
          ],
        ),
      ),
    );
  }

  // شريط التطبيق العلوي
  Widget _buildAppBar() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: Colors.white,
      child: Row(
        children: [
          IconButton(
            icon: Icon(Icons.arrow_back_ios, color: Colors.grey),
            onPressed: () => Navigator.of(context).pop(),
          ),
          Expanded(
            child: Text(
              'الحضور والانصراف',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.refresh, color: Colors.grey),
            onPressed: _loadAttendanceData,
          ),
        ],
      ),
    );
  }

  // قسم ملخص المعلومات
  Widget _buildSummarySection() {
    return Container(
      padding: EdgeInsets.symmetric(vertical: 16),
      color: Color(0xFFF9F5FF),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildInfoCard('وقت العمل اليوم', workingHours),
          _buildInfoCard('عدد الطلبات', requestCount.toString()),
        ],
      ),
    );
  }

  // بطاقة معلومات
  Widget _buildInfoCard(String title, String value) {
    return Column(
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  // المحتوى الرئيسي للصفحة
  Widget _buildMainContent() {
    return SingleChildScrollView(
      child: Column(
        children: [
          Container(
            padding: EdgeInsets.all(20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // عرض التاريخ الحالي
                Text(
                  DateFormat('EEEE, d MMMM yyyy').format(currentTime),
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w500,
                    color: Colors.grey[700],
                  ),
                ),
                SizedBox(height: 16),

                // عرض الوقت الحالي
                Text(
                  DateFormat('hh:mm a').format(currentTime),
                  style: TextStyle(
                    fontSize: 40,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 40),

                // حالة الحضور الحالية
                Text(
                  isCheckedIn ? 'تم تسجيل الحضور' : 'لم يتم تسجيل الحضور',
                  style: TextStyle(
                    fontSize: 16,
                    color: isCheckedIn ? Colors.green : Colors.red,
                    fontWeight: FontWeight.w500,
                  ),
                ),

                // وقت تسجيل الحضور إذا كان متاحًا
                if (isCheckedIn && checkInTime != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Text(
                      'وقت الحضور: ${DateFormat('hh:mm a').format(checkInTime!)}',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                  ),

                SizedBox(height: 40),

                // زر تسجيل الحضور/الانصراف
                ElevatedButton(
                  onPressed: isLoading ? null : _toggleAttendance,
                  style: ElevatedButton.styleFrom(
                    foregroundColor: Colors.white,
                    backgroundColor: isCheckedIn ? Colors.redAccent : Colors.green,
                    padding: EdgeInsets.symmetric(horizontal: 50, vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                    elevation: 5,
                  ),
                  child: isLoading
                      ? SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                      : Text(
                    isCheckedIn ? 'تسجيل انصراف' : 'تسجيل حضور',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // سجل الحضور
          _buildAttendanceHistory(),
        ],
      ),
    );
  }

  // سجل الحضور
  Widget _buildAttendanceHistory() {
    return Container(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'سجل الحضور',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
          SizedBox(height: 12),

          attendanceRecords.isEmpty
              ? Center(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Text(
                'لا يوجد سجل حضور سابق',
                style: TextStyle(
                  color: Colors.grey,
                  fontSize: 16,
                ),
              ),
            ),
          )
              : Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 10,
                  offset: Offset(0, 3),
                ),
              ],
            ),
            child: ListView.separated(
              shrinkWrap: true,
              physics: NeverScrollableScrollPhysics(),
              itemCount: attendanceRecords.length,
              separatorBuilder: (context, index) => Divider(height: 1),
              itemBuilder: (context, index) {
                final record = attendanceRecords[index];
                return _buildRecordItem(record);
              },
            ),
          ),
        ],
      ),
    );
  }

  // عنصر سجل الحضور
  Widget _buildRecordItem(Map<String, dynamic> record) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      child: Row(
        children: [
          // التاريخ
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                record['date'] ?? '',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'المدة: ${record['duration'] ?? 'غير محدد'}',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 12,
                ),
              ),
            ],
          ),
          Spacer(),

          // وقت الحضور والانصراف
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _buildTimeChip(
                'الحضور',
                record['checkIn'] ?? '',
                Colors.green,
              ),
              SizedBox(height: 4),
              _buildTimeChip(
                'الانصراف',
                record['checkOut'] ?? 'لم يسجل',
                record['checkOut'] != null ? Colors.redAccent : Colors.grey,
              ),
            ],
          ),
        ],
      ),
    );
  }

  // شريحة الوقت
  Widget _buildTimeChip(String label, String time, Color color) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 11,
              color: color,
              fontWeight: FontWeight.w500,
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