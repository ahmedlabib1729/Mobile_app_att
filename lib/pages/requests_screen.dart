// pages/requests_screen.dart - شاشة الطلبات مع دعم الوضع غير المتصل
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/employee.dart';
import '../models/leave_request.dart';
import '../services/odoo_service.dart';
import '../services/offline_manager.dart';
import '../services/connectivity_service.dart';
import '../pages/new_leave_request_screen.dart';
import '../pages/leave_request_details_screen.dart';
import '../models/leave_type.dart';

class RequestsScreen extends StatefulWidget {
  final OdooService odooService;
  final Employee employee;

  const RequestsScreen({
    Key? key,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _RequestsScreenState createState() => _RequestsScreenState();
}

class _RequestsScreenState extends State<RequestsScreen>
    with SingleTickerProviderStateMixin {

  late TabController _tabController;
  final ConnectivityService _connectivityService = ConnectivityService();
  final OfflineManager _offlineManager = OfflineManager();

  // البيانات
  List<LeaveRequest> allRequests = [];
  List<LeaveRequest> pendingRequests = [];
  List<LeaveRequest> approvedRequests = [];
  List<LeaveRequest> rejectedRequests = [];

  // حالة التطبيق
  bool isLoading = true;
  bool isOnline = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();

    // تهيئة التبويبات
    _tabController = TabController(length: 4, vsync: this);

    // مراقبة حالة الاتصال
    _connectivityService.connectionStatusStream.listen((isConnected) {
      if (mounted) {
        setState(() {
          isOnline = isConnected;
        });

        if (isConnected) {
          _syncData();
        }
      }
    });

    // تحميل البيانات الأولية
    _loadRequests();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  // تحميل الطلبات
  Future<void> _loadRequests() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      List<LeaveRequest> requests;

      if (isOnline) {
        // تحميل من الخادم
        requests = await widget.odooService.getLeaveRequests(widget.employee.id);

        // حفظ في التخزين المحلي
        await _offlineManager.saveLeaveRequests(requests);
      } else {
        // تحميل من التخزين المحلي
        requests = await _offlineManager.getOfflineLeaveRequests(widget.employee.id);
      }

      // تصنيف الطلبات
      _categorizeRequests(requests);

      setState(() {
        isLoading = false;
      });

    } catch (e) {
      print('خطأ في تحميل الطلبات: $e');
      setState(() {
        isLoading = false;
        errorMessage = 'خطأ في تحميل الطلبات: ${e.toString()}';
      });
    }
  }

  // تصنيف الطلبات حسب الحالة
  void _categorizeRequests(List<LeaveRequest> requests) {
    allRequests = requests;
    pendingRequests = requests.where((r) => r.state == 'draft' || r.state == 'confirm').toList();
    approvedRequests = requests.where((r) => r.state == 'validate' || r.state == 'validate1').toList();
    rejectedRequests = requests.where((r) => r.state == 'refuse').toList();
  }

  // مزامنة البيانات
  Future<void> _syncData() async {
    if (!isOnline) return;

    try {
      // مزامنة الطلبات المؤجلة
      await _offlineManager.syncPendingLeaveRequests();

      // إعادة تحميل البيانات
      await _loadRequests();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('تمت مزامنة البيانات بنجاح'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      print('خطأ في المزامنة: $e');
    }
  }

  // إنشاء طلب جديد
  Future<void> _createNewRequest() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => NewLeaveRequestScreen(
          odooService: widget.odooService,
          employee: widget.employee,
        ),
      ),
    );

    // إعادة تحميل البيانات إذا تم إنشاء طلب جديد
    if (result == true) {
      _loadRequests();
    }
  }

  // عرض تفاصيل الطلب
  void _viewRequestDetails(LeaveRequest request) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => LeaveRequestDetailsScreen(
          request: request,
          odooService: widget.odooService,
          employee: widget.employee,
        ),
      ),
    ).then((_) {
      // إعادة تحميل البيانات عند العودة
      _loadRequests();
    });
  }

  // حذف الطلب
  Future<void> _cancelRequest(LeaveRequest request) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('تأكيد الإلغاء'),
        content: Text('هل أنت متأكد من رغبتك في إلغاء هذا الطلب؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('لا'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: Text('نعم، إلغاء', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await widget.odooService.cancelLeaveRequest(request.id);

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('تم إلغاء الطلب بنجاح'),
            backgroundColor: Colors.green,
          ),
        );

        // إعادة تحميل البيانات
        _loadRequests();
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('خطأ في إلغاء الطلب: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFFF5F5F5),
      appBar: AppBar(
        title: Text('طلبات الإجازات'),
        backgroundColor: Colors.white,
        elevation: 1,
        actions: [
          // مؤشر حالة الاتصال
          if (!isOnline)
            Container(
              padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              margin: EdgeInsets.symmetric(horizontal: 8),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.wifi_off, color: Colors.white, size: 16),
                  SizedBox(width: 4),
                  Text(
                    'غير متصل',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ],
              ),
            ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadRequests,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: [
            Tab(
              text: 'الكل (${allRequests.length})',
              icon: Icon(Icons.list),
            ),
            Tab(
              text: 'قيد الانتظار (${pendingRequests.length})',
              icon: Icon(Icons.schedule),
            ),
            Tab(
              text: 'مقبولة (${approvedRequests.length})',
              icon: Icon(Icons.check_circle),
            ),
            Tab(
              text: 'مرفوضة (${rejectedRequests.length})',
              icon: Icon(Icons.cancel),
            ),
          ],
        ),
      ),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : errorMessage != null
          ? _buildErrorWidget()
          : TabBarView(
        controller: _tabController,
        children: [
          _buildRequestsList(allRequests),
          _buildRequestsList(pendingRequests),
          _buildRequestsList(approvedRequests),
          _buildRequestsList(rejectedRequests),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _createNewRequest,
        icon: Icon(Icons.add),
        label: Text('طلب جديد'),
        backgroundColor: Colors.blue,
      ),
    );
  }

  // ويدجت عرض الأخطاء
  Widget _buildErrorWidget() {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            SizedBox(height: 16),
            Text(
              errorMessage!,
              style: TextStyle(fontSize: 16),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _loadRequests,
              child: Text('إعادة المحاولة'),
            ),
          ],
        ),
      ),
    );
  }

  // ويدجت قائمة الطلبات
  Widget _buildRequestsList(List<LeaveRequest> requests) {
    if (requests.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.inbox,
              size: 64,
              color: Colors.grey,
            ),
            SizedBox(height: 16),
            Text(
              'لا توجد طلبات',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey[600],
              ),
            ),
            SizedBox(height: 8),
            Text(
              'يمكنك إنشاء طلب إجازة جديد بالضغط على الزر أدناه',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[500],
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadRequests,
      child: ListView.builder(
        padding: EdgeInsets.all(16),
        itemCount: requests.length,
        itemBuilder: (context, index) {
          final request = requests[index];
          return _buildRequestCard(request);
        },
      ),
    );
  }

  // بطاقة الطلب
  Widget _buildRequestCard(LeaveRequest request) {
    return Card(
      margin: EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        onTap: () => _viewRequestDetails(request),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // رأس البطاقة
              Row(
                children: [
                  // نوع الإجازة
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Color(int.parse('0xFF${request.stateColor.substring(1)}')).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      request.leaveTypeName,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Color(int.parse('0xFF${request.stateColor.substring(1)}')),
                      ),
                    ),
                  ),
                  Spacer(),
                  // حالة الطلب
                  Row(
                    children: [
                      Text(
                        request.stateIcon,
                        style: TextStyle(fontSize: 16),
                      ),
                      SizedBox(width: 4),
                      Text(
                        request.stateText,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Color(int.parse('0xFF${request.stateColor.substring(1)}')),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              SizedBox(height: 12),

              // معلومات الطلب
              Row(
                children: [
                  Icon(Icons.calendar_today, size: 16, color: Colors.grey),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      request.formattedDateRange,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  Text(
                    request.formattedDuration,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue,
                    ),
                  ),
                ],
              ),

              if (request.reason.isNotEmpty) ...[
                SizedBox(height: 8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.description, size: 16, color: Colors.grey),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        request.reason,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],

              // أزرار الإجراءات (للطلبات قيد الانتظار فقط)
              if (request.state == 'draft' || request.state == 'confirm') ...[
                SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton.icon(
                      onPressed: () => _cancelRequest(request),
                      icon: Icon(Icons.delete, size: 16, color: Colors.red),
                      label: Text(
                        'إلغاء',
                        style: TextStyle(color: Colors.red),
                      ),
                    ),
                    SizedBox(width: 8),
                    TextButton.icon(
                      onPressed: () => _viewRequestDetails(request),
                      icon: Icon(Icons.visibility, size: 16),
                      label: Text('عرض'),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}