// pages/home_page.dart - محدث مع زر الطلبات - مُصحح
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:login_app/pages/profile_page.dart';
import 'dart:async';
import '../models/employee.dart';
import '../services/odoo_service.dart';
import '../services/offline_manager.dart';
import '../services/connectivity_service.dart';
import '../pages/attendance_screen.dart';
import '../pages/requests_screen.dart';
import '../pages/login_page.dart';
import '../widgets/employee_avatar.dart';

class HomePage extends StatefulWidget {
  final OdooService odooService;
  final Employee employee;

  const HomePage({
    Key? key,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ConnectivityService _connectivityService = ConnectivityService();
  final OfflineManager _offlineManager = OfflineManager();

  DateTime currentTime = DateTime.now();
  Timer? _timer;

  // حالة الاتصال
  bool isOnline = true;
  int pendingActionsCount = 0;

  // بيانات الحضور
  bool isCheckedIn = false;
  DateTime? checkInTime;
  String workingHours = "0:00";

  // حالة التحميل
  bool isLoading = true;

  @override
  void initState() {
    super.initState();

    // تهيئة الخدمات
    _offlineManager.initialize(widget.odooService);

    // تحديث الوقت كل ثانية
    _timer = Timer.periodic(Duration(seconds: 1), (timer) {
      setState(() {
        currentTime = DateTime.now();
        _updateWorkingHours();
      });
    });

    // مراقبة حالة الاتصال
    _connectivityService.connectionStatusStream.listen((isConnected) {
      setState(() {
        isOnline = isConnected;
      });

      if (isConnected) {
        _syncDataWhenOnline();
      }
    });

    // تحميل البيانات الأولية
    _loadInitialData();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  // تحميل البيانات الأولية
  Future<void> _loadInitialData() async {
    try {
      setState(() {
        isLoading = true;
      });

      // تحميل حالة الحضور
      await _loadAttendanceStatus();

      // تحميل عدد الإجراءات المؤجلة
      await _loadPendingActionsCount();

      setState(() {
        isLoading = false;
      });
    } catch (e) {
      print('خطأ في تحميل البيانات الأولية: $e');
      setState(() {
        isLoading = false;
      });
    }
  }

  // تحميل حالة الحضور
  Future<void> _loadAttendanceStatus() async {
    try {
      Map<String, dynamic> status;

      if (isOnline) {
        status = await widget.odooService.getCurrentAttendanceStatus(widget.employee.id);
      } else {
        status = await _offlineManager.getOfflineAttendanceStatus(widget.employee.id);
      }

      setState(() {
        isCheckedIn = status['is_checked_in'] ?? false;

        if (isCheckedIn && status['check_in'] != null) {
          checkInTime = DateTime.parse(status['check_in']);
          _updateWorkingHours();
        }
      });
    } catch (e) {
      print('خطأ في تحميل حالة الحضور: $e');
    }
  }

  // تحميل عدد الإجراءات المؤجلة
  Future<void> _loadPendingActionsCount() async {
    try {
      final count = await _offlineManager.getPendingActionsCount();
      setState(() {
        pendingActionsCount = count;
      });
    } catch (e) {
      print('خطأ في تحميل عدد الإجراءات المؤجلة: $e');
    }
  }

  // تحديث ساعات العمل
  void _updateWorkingHours() {
    if (isCheckedIn && checkInTime != null) {
      final Duration workDuration = currentTime.difference(checkInTime!);
      final int hours = workDuration.inHours;
      final int minutes = (workDuration.inMinutes % 60);
      workingHours = "$hours:${minutes.toString().padLeft(2, '0')}";
    }
  }

  // مزامنة البيانات عند الاتصال
  Future<void> _syncDataWhenOnline() async {
    if (!isOnline) return;

    try {
      // مزامنة الإجراءات المؤجلة
      await _offlineManager.syncOfflineActions();

      // تحديث البيانات
      await _loadAttendanceStatus();
      await _loadPendingActionsCount();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('تمت مزامنة البيانات بنجاح'),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 2),
        ),
      );
    } catch (e) {
      print('خطأ في المزامنة: $e');
    }
  }

  // تسجيل الخروج
  Future<void> _logout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('تأكيد تسجيل الخروج'),
        content: Text('هل أنت متأكد من رغبتك في تسجيل الخروج؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: Text('تسجيل خروج', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await widget.odooService.logout();

        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (context) => LoginPage()),
              (route) => false,
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('خطأ في تسجيل الخروج: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Color(0xFFF5F5F5),
      appBar: AppBar(
        title: Text('مرحباً ${widget.employee.name}'),
        backgroundColor: Colors.white,
        elevation: 1,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadInitialData,
          ),
          IconButton(
            icon: Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            // معلومات الموظف
            _buildEmployeeCard(),
            SizedBox(height: 20),

            // بطاقات الإحصائيات
            _buildStatsCards(),
            SizedBox(height: 20),

            // أزرار الإجراءات
            _buildActionButtons(),
            SizedBox(height: 20),

            // معلومات إضافية
            _buildAdditionalInfo(),
          ],
        ),
      ),
    );
  }

// تحديث دالة _buildEmployeeCard في HomePage لإضافة صورة الموظف

  Widget _buildEmployeeCard() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            // صورة الموظف
            AdvancedEmployeeAvatar(
              employee: widget.employee,
              radius: 40,
              showBorder: true,
              borderColor: Colors.blue,
              showBadge: isCheckedIn, // إظهار شارة إذا كان مسجل حضور
              statusColor: isCheckedIn ? Colors.green : Colors.grey,
              odooService: widget.odooService,
              onTap: () {
                // الانتقال إلى صفحة الملف الشخصي
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => ProfilePage(
                      odooService: widget.odooService,
                      initialEmployee: widget.employee,
                    ),
                  ),
                );
              },
            ),
            SizedBox(height: 12),
            Text(
              widget.employee.name,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            Text(
              widget.employee.jobTitle,
              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            ),
            Text(
              widget.employee.department,
              style: TextStyle(fontSize: 14, color: Colors.grey[500]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsCards() {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            'وقت العمل اليوم',
            workingHours,
            Icons.access_time,
            Colors.blue,
          ),
        ),
        SizedBox(width: 16),
        Expanded(
          child: _buildStatCard(
            'الطلبات المؤجلة',
            pendingActionsCount.toString(),
            Icons.pending_actions,
            Colors.orange,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, size: 32, color: color),
            SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              title,
              style: TextStyle(fontSize: 12, color: Colors.grey[600]),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Column(
      children: [
        // زر الحضور والانصراف
        SizedBox(
          width: double.infinity,
          height: 60,
          child: ElevatedButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => AttendanceScreen(
                    odooService: widget.odooService,
                    employee: widget.employee,
                  ),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: isCheckedIn ? Colors.red : Colors.green,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  isCheckedIn ? Icons.logout : Icons.login,
                  color: Colors.white,
                ),
                SizedBox(width: 8),
                Text(
                  isCheckedIn ? 'إدارة الحضور' : 'تسجيل حضور',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),

        SizedBox(height: 16),

        // زر الطلبات
        SizedBox(
          width: double.infinity,
          height: 60,
          child: ElevatedButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => RequestsScreen(
                    odooService: widget.odooService,
                    employee: widget.employee,
                  ),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blue,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.assignment, color: Colors.white),
                SizedBox(width: 8),
                Text(
                  'طلبات الإجازات',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAdditionalInfo() {
    return Card(
      elevation: 2,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'معلومات إضافية',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  isOnline ? Icons.wifi : Icons.wifi_off,
                  color: isOnline ? Colors.green : Colors.red,
                ),
                SizedBox(width: 8),
                Text(
                  isOnline ? 'متصل' : 'غير متصل',
                  style: TextStyle(
                    color: isOnline ? Colors.green : Colors.red,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
            if (pendingActionsCount > 0) ...[
              SizedBox(height: 8),
              Row(
                children: [
                  Icon(Icons.sync_problem, color: Colors.orange),
                  SizedBox(width: 8),
                  Text(
                    'لديك $pendingActionsCount إجراء في انتظار المزامنة',
                    style: TextStyle(color: Colors.orange),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}