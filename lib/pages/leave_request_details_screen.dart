// lib/pages/leave_request_details_screen.dart - Modern & English
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/leave_request.dart';
import '../models/employee.dart';
import '../services/leave_service.dart';
import '../services/odoo_service.dart';

class LeaveRequestDetailsScreen extends StatefulWidget {
  final LeaveRequest request;
  final OdooService odooService;
  final Employee employee;

  const LeaveRequestDetailsScreen({
    Key? key,
    required this.request,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _LeaveRequestDetailsScreenState createState() => _LeaveRequestDetailsScreenState();
}

class _LeaveRequestDetailsScreenState extends State<LeaveRequestDetailsScreen> {
  late LeaveService _leaveService;
  late LeaveRequest currentRequest;
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    _leaveService = LeaveService(widget.odooService);
    currentRequest = widget.request;
  }

  Future<void> _cancelRequest() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Cancel Confirmation'),
        content: Text('Are you sure you want to cancel this leave request?'),
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

    if (confirmed != true) return;

    try {
      setState(() {
        isLoading = true;
      });

      final result = await _leaveService.cancelLeaveRequest(currentRequest.id);

      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? 'Request cancelled successfully'),
            backgroundColor: result['offline'] == true ? Colors.orange : Colors.green,
          ),
        );
        Navigator.of(context).pop(true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['error'] ?? 'Failed to cancel the request'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
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
      backgroundColor: const Color(0xFFF6F8FC),
      body: SafeArea(
        child: Column(
          children: [
            _buildAppBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(18),
                child: Column(
                  children: [
                    _buildStatusCard(),
                    SizedBox(height: 16),
                    _buildDetailsCard(),
                    SizedBox(height: 16),
                    _buildTimelineCard(),
                    if (currentRequest.managerComment?.isNotEmpty == true) ...[
                      SizedBox(height: 16),
                      _buildCommentsCard(),
                    ],
                    SizedBox(height: 80),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _buildBottomActions(),
    );
  }

  Widget _buildAppBar() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: Colors.white,
      child: Row(
        children: [
          IconButton(
            icon: Icon(Icons.arrow_back_ios, color: Colors.grey[600]),
            onPressed: () => Navigator.of(context).pop(),
          ),
          Expanded(
            child: Text(
              'Leave Request Details',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF222B45),
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.share, color: Colors.grey),
            onPressed: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildStatusCard() {
    final mainColor = Color(int.parse('0xFF${currentRequest.stateColor.substring(1)}'));
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            mainColor,
            mainColor.withOpacity(0.8),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: mainColor.withOpacity(0.23),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            currentRequest.stateIcon,
            style: TextStyle(fontSize: 54),
          ),
          SizedBox(height: 8),
          Text(
            currentRequest.stateText,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          SizedBox(height: 4),
          Text(
            currentRequest.leaveTypeName,
            style: TextStyle(
              fontSize: 17,
              color: Colors.white.withOpacity(0.92),
            ),
          ),
          SizedBox(height: 13),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.23),
              borderRadius: BorderRadius.circular(22),
            ),
            child: Text(
              currentRequest.formattedDuration,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.white,
                letterSpacing: 1,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailsCard() {
    return Container(
      padding: EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Leave Details',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF222B45),
            ),
          ),
          SizedBox(height: 16),

          _buildDetailRow(
            icon: Icons.category,
            label: 'Leave Type',
            value: currentRequest.leaveTypeName,
          ),
          _buildDetailRow(
            icon: Icons.calendar_today,
            label: 'Start Date',
            value: DateFormat('EEEE, d MMM yyyy').format(currentRequest.startDate),
          ),
          _buildDetailRow(
            icon: Icons.event,
            label: 'End Date',
            value: DateFormat('EEEE, d MMM yyyy').format(currentRequest.endDate),
          ),
          _buildDetailRow(
            icon: Icons.access_time,
            label: 'Days',
            value: currentRequest.formattedDuration,
          ),

          if (currentRequest.reason.isNotEmpty)
            _buildDetailRow(
              icon: Icons.description,
              label: 'Reason',
              value: currentRequest.reason,
              isMultiLine: true,
            ),

          _buildDetailRow(
            icon: Icons.person,
            label: 'Employee',
            value: currentRequest.employeeName ?? 'N/A',
          ),
          _buildDetailRow(
            icon: Icons.pending_actions,
            label: 'Request Date',
            value: DateFormat('d MMM yyyy - hh:mm a').format(currentRequest.requestDate),
          ),

          if (currentRequest.approvalDate != null)
            _buildDetailRow(
              icon: Icons.check_circle,
              label: 'Approval Date',
              value: DateFormat('d MMM yyyy - hh:mm a').format(currentRequest.approvalDate!),
            ),

          if (currentRequest.approverName != null)
            _buildDetailRow(
              icon: Icons.supervisor_account,
              label: 'Approved By',
              value: currentRequest.approverName!,
            ),
        ],
      ),
    );
  }

  Widget _buildDetailRow({
    required IconData icon,
    required String label,
    required String value,
    bool isMultiLine = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(bottom: 15),
      child: Row(
        crossAxisAlignment: isMultiLine ? CrossAxisAlignment.start : CrossAxisAlignment.center,
        children: [
          Container(
            padding: EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(9),
            ),
            child: Icon(icon, size: 21, color: Colors.blueGrey),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey[600],
                    fontWeight: FontWeight.w500,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineCard() {
    return Container(
      padding: EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Timeline',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF222B45),
            ),
          ),
          SizedBox(height: 15),

          _buildTimelineItem(
            icon: Icons.add_circle,
            title: 'Request Created',
            subtitle: DateFormat('d MMM yyyy - hh:mm a').format(currentRequest.requestDate),
            isCompleted: true,
          ),
          if (currentRequest.state != 'draft')
            _buildTimelineItem(
              icon: Icons.send,
              title: 'Submitted for Review',
              subtitle: 'Awaiting Manager Approval',
              isCompleted: true,
            ),
          if (currentRequest.state == 'validate1')
            _buildTimelineItem(
              icon: Icons.visibility,
              title: 'Under Review',
              subtitle: 'Manager is reviewing your request',
              isCompleted: true,
              isActive: true,
            ),
          if (currentRequest.state == 'validate')
            _buildTimelineItem(
              icon: Icons.check_circle,
              title: 'Request Approved',
              subtitle: currentRequest.approvalDate != null
                  ? DateFormat('d MMM yyyy - hh:mm a').format(currentRequest.approvalDate!)
                  : 'Approved',
              isCompleted: true,
            ),
          if (currentRequest.state == 'refuse')
            _buildTimelineItem(
              icon: Icons.cancel,
              title: 'Request Refused',
              subtitle: currentRequest.managerComment ?? 'Refused by Manager',
              isCompleted: true,
              isRejected: true,
            ),
          if (currentRequest.state == 'cancel')
            _buildTimelineItem(
              icon: Icons.block,
              title: 'Request Cancelled',
              subtitle: 'Cancelled by Employee',
              isCompleted: true,
              isRejected: true,
            ),
        ],
      ),
    );
  }

  Widget _buildTimelineItem({
    required IconData icon,
    required String title,
    required String subtitle,
    bool isCompleted = false,
    bool isActive = false,
    bool isRejected = false,
  }) {
    Color color;
    if (isRejected) {
      color = Colors.red;
    } else if (isActive) {
      color = Colors.orange;
    } else if (isCompleted) {
      color = Colors.green;
    } else {
      color = Colors.grey;
    }

    return Padding(
      padding: EdgeInsets.only(bottom: 14),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withOpacity(0.12),
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 2),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.bold,
                    color: isActive ? color : Colors.black,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommentsCard() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.09),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.comment, color: Color(0xFF2196F3)),
              SizedBox(width: 8),
              Text(
                'Manager Comments',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF222B45),
                ),
              ),
            ],
          ),
          SizedBox(height: 13),
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.07),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.withOpacity(0.23)),
            ),
            child: Text(
              currentRequest.managerComment!,
              style: TextStyle(
                fontSize: 14.2,
                color: Colors.blue[800],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomActions() {
    if (!currentRequest.canCancel && !currentRequest.canEdit) {
      return SizedBox.shrink();
    }

    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.11),
            blurRadius: 5,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          if (currentRequest.canEdit) ...[
            Expanded(
              child: OutlinedButton(
                onPressed: isLoading
                    ? null
                    : () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Edit feature coming soon!')),
                  );
                },
                style: OutlinedButton.styleFrom(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  side: BorderSide(color: Color(0xFF2196F3)),
                ),
                child: Text(
                  'Edit',
                  style: TextStyle(fontSize: 16),
                ),
              ),
            ),
            if (currentRequest.canCancel) SizedBox(width: 16),
          ],
          if (currentRequest.canCancel)
            Expanded(
              child: ElevatedButton(
                onPressed: isLoading ? null : _cancelRequest,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                  padding: EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
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
                  'Cancel Request',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
