// pages/home_page.dart - محدث مع نظام اللغات وزر التقويم

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:login_app/pages/profile_page.dart';
import 'dart:async';
import '../models/employee.dart';
import '../services/odoo_service.dart';
import '../services/offline_manager.dart';
import '../services/connectivity_service.dart';
import '../services/language_manager.dart';
import '../widgets/language_switcher.dart';
import '../pages/attendance_screen.dart';
import '../pages/requests_screen.dart';
import '../pages/login_page.dart';
import '../widgets/employee_avatar.dart';
import '../pages/announcements_screen.dart';
import '../pages/payslips_screen.dart';
import '../pages/calendar_screen.dart'; // إضافة استيراد صفحة التقويم

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

  // Connection status
  bool isOnline = true;
  int pendingActionsCount = 0;

  // Attendance data
  bool isCheckedIn = false;
  DateTime? checkInTime;
  String workingHours = "0:00";

  // Loading status
  bool isLoading = true;

  @override
  void initState() {
    super.initState();

    _offlineManager.initialize(widget.odooService);

    _timer = Timer.periodic(Duration(seconds: 1), (timer) {
      setState(() {
        currentTime = DateTime.now();
        _updateWorkingHours();
      });
    });

    _connectivityService.connectionStatusStream.listen((isConnected) {
      setState(() {
        isOnline = isConnected;
      });

      if (isConnected) {
        _syncDataWhenOnline();
      }
    });

    _loadInitialData();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _loadInitialData() async {
    try {
      setState(() {
        isLoading = true;
      });

      await _loadAttendanceStatus();
      await _loadPendingActionsCount();

      setState(() {
        isLoading = false;
      });
    } catch (e) {
      print('Error loading initial data: $e');
      setState(() {
        isLoading = false;
      });
    }
  }

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
          // تحليل الوقت وتحويله من UTC إلى المحلي
          String checkInString = status['check_in'];
          DateTime parsedTime;

          // إذا كان الوقت ينتهي بـ Z فهو UTC
          if (checkInString.endsWith('Z')) {
            parsedTime = DateTime.parse(checkInString);
          } else {
            // افترض أنه UTC وأضف Z
            parsedTime = DateTime.parse(checkInString + 'Z');
          }

          // تحويل إلى الوقت المحلي
          checkInTime = parsedTime.toLocal();

          print('وقت الحضور UTC: $parsedTime');
          print('وقت الحضور المحلي: $checkInTime');

          _updateWorkingHours();
        } else {
          checkInTime = null;
          workingHours = "0:00";
        }
      });
    } catch (e) {
      print('Error loading attendance status: $e');
      setState(() {
        isCheckedIn = false;
        checkInTime = null;
        workingHours = "0:00";
      });
    }
  }

  Future<void> _loadPendingActionsCount() async {
    try {
      final count = await _offlineManager.getPendingActionsCount();
      setState(() {
        pendingActionsCount = count;
      });
    } catch (e) {
      print('Error loading pending actions count: $e');
    }
  }

  void _updateWorkingHours() {
    if (isCheckedIn && checkInTime != null) {
      final Duration workDuration = currentTime.difference(checkInTime!);
      final int hours = workDuration.inHours;
      final int minutes = (workDuration.inMinutes % 60);
      workingHours = "$hours:${minutes.toString().padLeft(2, '0')}";
    }
  }

  Future<void> _syncDataWhenOnline() async {
    if (!isOnline) return;

    try {
      await _offlineManager.syncOfflineActions();
      await _loadAttendanceStatus();
      await _loadPendingActionsCount();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.lang.translate('data_synced')),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 2),
        ),
      );
    } catch (e) {
      print('Error syncing data: $e');
    }
  }

  Future<void> _logout() async {
    final lang = context.lang;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        title: Row(
          children: [
            Container(
              padding: EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.logout, color: Colors.red, size: 20),
            ),
            SizedBox(width: 12),
            Text(lang.translate('logout_confirmation')),
          ],
        ),
        content: Text(lang.translate('logout_message')),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(lang.translate('cancel'), style: TextStyle(color: Colors.grey[600])),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: Text(lang.translate('logout'), style: TextStyle(color: Colors.white)),
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
            content: Text('${lang.translate('error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = context.lang;

    if (isLoading) {
      return Scaffold(
        backgroundColor: Color(0xFFF8F9FD),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF2196F3)),
              ),
              SizedBox(height: 20),
              Text(
                lang.translate('loading_data'),
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Format date based on language
    String formattedDate;
    if (lang.isArabic) {
      var formatter = DateFormat('EEEE، d MMMM yyyy', 'ar');
      formattedDate = formatter.format(currentTime);
    } else {
      formattedDate = DateFormat('EEEE, d MMMM yyyy').format(currentTime);
    }

    return Scaffold(
      backgroundColor: Color(0xFFF8F9FD),
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 120,
            floating: false,
            pinned: true,
            backgroundColor: Color(0xFF2196F3),
            elevation: 0,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color(0xFF2196F3),
                      Color(0xFF1976D2),
                    ],
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: EdgeInsets.only(left: 16, right: 16, top: 40),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${lang.translate('welcome')}، ${widget.employee.name.split(' ')[0]} 👋',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          formattedDate,
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.white.withOpacity(0.8),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            actions: [
              // زر تغيير اللغة
              LanguageSwitcher(
                showText: false,
                iconColor: Colors.white,
                backgroundColor: Colors.white.withOpacity(0.2),
              ),
              IconButton(
                icon: Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.refresh, color: Colors.white, size: 20),
                ),
                onPressed: _loadInitialData,
                tooltip: lang.translate('refresh'),
              ),
              IconButton(
                icon: Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.logout, color: Colors.white, size: 20),
                ),
                onPressed: _logout,
                tooltip: lang.translate('logout'),
              ),
              SizedBox(width: 8),
            ],
          ),

          SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                children: [
                  _buildEmployeeCard(),
                  SizedBox(height: 20),
                  _buildStatsCards(),
                  SizedBox(height: 20),
                  _buildActionButtons(),
                  SizedBox(height: 20),
                  _buildAdditionalInfo(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmployeeCard() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white,
            Colors.blue.withOpacity(0.03),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 20,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
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
          borderRadius: BorderRadius.circular(20),
          child: Padding(
            padding: EdgeInsets.all(20),
            child: Row(
              children: [
                Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.blue.withOpacity(0.2),
                        blurRadius: 15,
                        offset: Offset(0, 5),
                      ),
                    ],
                  ),
                  child: AdvancedEmployeeAvatar(
                    employee: widget.employee,
                    radius: 35,
                    showBorder: true,
                    borderColor: Colors.white,
                    borderWidth: 3,
                    showBadge: isCheckedIn,
                    statusColor: isCheckedIn ? Colors.green : Colors.grey,
                    odooService: widget.odooService,
                  ),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.employee.name,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1A1A1A),
                        ),
                      ),
                      SizedBox(height: 4),
                      Container(
                        padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Color(0xFF2196F3).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          widget.employee.jobTitle,
                          style: TextStyle(
                            fontSize: 13,
                            color: Color(0xFF2196F3),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.business, size: 14, color: Colors.grey[600]),
                          SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              widget.employee.department,
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
                  ),
                ),
                Icon(
                  Icons.arrow_forward_ios,
                  color: Colors.grey[400],
                  size: 16,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatsCards() {
    final hours = workingHours.split(':')[0].padLeft(2, '0');
    final minutes = workingHours.split(':')[1].padLeft(2, '0');

    return Container(
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF2196F3),
            Color(0xFF1565C0),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Color(0xFF2196F3).withOpacity(0.3),
            blurRadius: 15,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            context.lang.translate('todays_working_hours'),
            style: TextStyle(
              color: Colors.white.withOpacity(0.9),
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
          SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // الساعات
              Column(
                children: [
                  Text(
                    hours,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 48,
                      fontWeight: FontWeight.bold,
                      height: 1,
                    ),
                  ),
                  Text(
                    context.lang.isArabic ? 'ساعة' : 'Hours',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
              // الفاصل
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: Text(
                  ':',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 36,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              // الدقائق
              Column(
                children: [
                  Text(
                    minutes,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 48,
                      fontWeight: FontWeight.bold,
                      height: 1,
                    ),
                  ),
                  Text(
                    context.lang.isArabic ? 'دقيقة' : 'Minutes',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ],
          ),
          if (checkInTime != null) ...[
            SizedBox(height: 16),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                '${context.lang.translate('Check in at')} ${DateFormat('hh:mm a').format(checkInTime!)}',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.1),
            blurRadius: 15,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          SizedBox(height: 12),
          Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1A1A1A),
            ),
          ),
          SizedBox(height: 4),
          Text(
            title,
            style: TextStyle(
              fontSize: 13,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    final lang = context.lang;

    return Column(
      children: [
        // زر الحضور الرئيسي
        Container(
          width: double.infinity,
          height: 70,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isCheckedIn
                  ? [Color(0xFFE53935), Color(0xFFD32F2F)]
                  : [Color(0xFF43A047), Color(0xFF388E3C)],
            ),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: (isCheckedIn ? Colors.red : Colors.green).withOpacity(0.3),
                blurRadius: 20,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
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
              borderRadius: BorderRadius.circular(20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    isCheckedIn ? Icons.logout : Icons.login,
                    color: Colors.white,
                    size: 32,
                  ),
                  SizedBox(width: 16),
                  Text(
                    isCheckedIn ? lang.translate('manage_attendance') : lang.translate('check_in'),
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        SizedBox(height: 24), // مساحة أكبر

        // Grid للأزرار الأخرى
        GridView.count(
          shrinkWrap: true,
          physics: NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          mainAxisSpacing: 16,
          crossAxisSpacing: 16,
          childAspectRatio: 1.3, // نسبة العرض للطول
          children: [
            _buildServiceCard(
              title: lang.translate('leaves'),
              icon: Icons.beach_access,
              gradientColors: [Color(0xFF1E88E5), Color(0xFF1976D2)],
              onTap: () {
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
            ),
            _buildServiceCard(
              title: lang.translate('announcements'),
              icon: Icons.campaign,
              gradientColors: [Color(0xFFFF6F00), Color(0xFFE65100)],
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => AnnouncementsScreen(
                      odooService: widget.odooService,
                      employee: widget.employee,
                    ),
                  ),
                );
              },
            ),
            _buildServiceCard(
              title: lang.translate('payslips'),
              icon: Icons.receipt_long,
              gradientColors: [Color(0xFF9C27B0), Color(0xFF7B1FA2)],
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => PayslipsScreen(
                      odooService: widget.odooService,
                      employee: widget.employee,
                    ),
                  ),
                );
              },
            ),
            // زر التقويم بدلاً من زر "المزيد"
            _buildServiceCard(
              title: lang.isArabic ? 'التقويم' : 'Calendar',
              icon: Icons.calendar_today,
              gradientColors: [Color(0xFF00BCD4), Color(0xFF0097A7)],
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => CalendarScreen(),
                  ),
                );
              },
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildServiceCard({
    required String title,
    required IconData icon,
    required List<Color> gradientColors,
    required VoidCallback onTap,
  }) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: gradientColors,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: gradientColors[0].withOpacity(0.3),
            blurRadius: 15,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(20),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: Colors.white, size: 32),
              ),
              SizedBox(height: 12),
              Text(
                title,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAdditionalInfo() {
    final lang = context.lang;

    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 15,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Color(0xFF2196F3).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.info_outline,
                  color: Color(0xFF2196F3),
                  size: 20,
                ),
              ),
              SizedBox(width: 12),
              Text(
                lang.translate('additional_info'),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A1A),
                ),
              ),
            ],
          ),
          SizedBox(height: 16),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: isOnline ? Colors.green.withOpacity(0.1) : Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isOnline ? Icons.wifi : Icons.wifi_off,
                  color: isOnline ? Colors.green : Colors.red,
                  size: 18,
                ),
                SizedBox(width: 8),
                Text(
                  isOnline ? lang.translate('online') : lang.translate('offline'),
                  style: TextStyle(
                    color: isOnline ? Colors.green : Colors.red,
                    fontWeight: FontWeight.w500,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}