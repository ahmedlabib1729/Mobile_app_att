// pages/requests_screen.dart - Modern UI + English
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/employee.dart';
import '../models/leave_request.dart';
import '../services/odoo_service.dart';
import '../services/offline_manager.dart';
import '../services/connectivity_service.dart';
import '../pages/new_leave_request_screen.dart';
import '../pages/leave_request_details_screen.dart';

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

  // Data
  List<LeaveRequest> allRequests = [];
  List<LeaveRequest> pendingRequests = [];
  List<LeaveRequest> approvedRequests = [];
  List<LeaveRequest> rejectedRequests = [];

  // App state
  bool isLoading = true;
  bool isOnline = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);

    _connectivityService.connectionStatusStream.listen((isConnected) {
      if (mounted) {
        setState(() {
          isOnline = isConnected;
        });
        if (isConnected) _syncData();
      }
    });

    _loadRequests();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadRequests() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      List<LeaveRequest> requests;

      if (isOnline) {
        requests = await widget.odooService.getLeaveRequests(widget.employee.id);
        await _offlineManager.saveLeaveRequests(requests);
      } else {
        requests = await _offlineManager.getOfflineLeaveRequests(widget.employee.id);
      }

      _categorizeRequests(requests);

      setState(() {
        isLoading = false;
      });

    } catch (e) {
      setState(() {
        isLoading = false;
        errorMessage = 'Error loading requests: ${e.toString()}';
      });
    }
  }

  void _categorizeRequests(List<LeaveRequest> requests) {
    allRequests = requests;
    pendingRequests = requests.where((r) => r.state == 'draft' || r.state == 'confirm').toList();
    approvedRequests = requests.where((r) => r.state == 'validate' || r.state == 'validate1').toList();
    rejectedRequests = requests.where((r) => r.state == 'refuse').toList();
  }

  Future<void> _syncData() async {
    if (!isOnline) return;

    try {
      await _offlineManager.syncPendingLeaveRequests();
      await _loadRequests();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Data synced successfully'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {}
  }

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
    if (result == true) {
      _loadRequests();
    }
  }

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
    ).then((_) => _loadRequests());
  }

  Future<void> _cancelRequest(LeaveRequest request) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Cancel Request'),
        content: Text('Are you sure you want to cancel this request?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('No'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: Text('Yes, Cancel', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await widget.odooService.cancelLeaveRequest(request.id);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Request cancelled successfully'),
            backgroundColor: Colors.green,
          ),
        );
        _loadRequests();
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to cancel: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFFF6F8FC),
      appBar: AppBar(
        title: Text('Leave Requests', style: TextStyle(color: Color(0xFF222B45))),
        backgroundColor: Colors.white,
        elevation: 1,
        iconTheme: IconThemeData(color: Color(0xFF222B45)),
        actions: [
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
                    'Offline',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ],
              ),
            ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadRequests,
            tooltip: 'Refresh',
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          indicatorColor: Color(0xFF2196F3),
          labelColor: Color(0xFF2196F3),
          unselectedLabelColor: Colors.grey,
          tabs: [
            Tab(
              text: 'All (${allRequests.length})',
              icon: Icon(Icons.list),
            ),
            Tab(
              text: 'Pending (${pendingRequests.length})',
              icon: Icon(Icons.schedule),
            ),
            Tab(
              text: 'Approved (${approvedRequests.length})',
              icon: Icon(Icons.check_circle),
            ),
            Tab(
              text: 'Rejected (${rejectedRequests.length})',
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
        label: Text('New Request'),
        backgroundColor: Color(0xFF2196F3),
      ),
    );
  }

  Widget _buildErrorWidget() {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red),
            SizedBox(height: 16),
            Text(
              errorMessage!,
              style: TextStyle(fontSize: 16),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _loadRequests,
              child: Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRequestsList(List<LeaveRequest> requests) {
    if (requests.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inbox, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No Requests',
              style: TextStyle(fontSize: 18, color: Colors.grey[600]),
            ),
            SizedBox(height: 8),
            Text(
              'Tap the button below to create a new leave request.',
              style: TextStyle(fontSize: 14, color: Colors.grey[500]),
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

  Widget _buildRequestCard(LeaveRequest request) {
    return Card(
      margin: EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(13),
      ),
      child: InkWell(
        onTap: () => _viewRequestDetails(request),
        borderRadius: BorderRadius.circular(13),
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Color(int.parse('0xFF${request.stateColor.substring(1)}')).withOpacity(0.13),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      request.leaveTypeName,
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.bold,
                        color: Color(int.parse('0xFF${request.stateColor.substring(1)}')),
                      ),
                    ),
                  ),
                  Spacer(),
                  Row(
                    children: [
                      Text(request.stateIcon, style: TextStyle(fontSize: 16)),
                      SizedBox(width: 4),
                      Text(
                        request.stateText,
                        style: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.bold,
                          color: Color(int.parse('0xFF${request.stateColor.substring(1)}')),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              SizedBox(height: 12),

              // Dates and Duration
              Row(
                children: [
                  Icon(Icons.calendar_today, size: 16, color: Colors.grey),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      request.formattedDateRange,
                      style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  Text(
                    request.formattedDuration,
                    style: TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2196F3),
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
                        style: TextStyle(fontSize: 12.5, color: Colors.grey[600]),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],

              // Actions for pending requests
              if (request.state == 'draft' || request.state == 'confirm') ...[
                SizedBox(height: 13),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton.icon(
                      onPressed: () => _cancelRequest(request),
                      icon: Icon(Icons.delete, size: 16, color: Colors.red),
                      label: Text('Cancel', style: TextStyle(color: Colors.red)),
                    ),
                    SizedBox(width: 8),
                    TextButton.icon(
                      onPressed: () => _viewRequestDetails(request),
                      icon: Icon(Icons.visibility, size: 16),
                      label: Text('View'),
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
