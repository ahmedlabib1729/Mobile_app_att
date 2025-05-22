// pages/leave_request_details_screen.dart - تفاصيل طلب الإجازة
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/leave_request.dart';
import '../models/employee.dart';
import '../services/leave_service.dart';
import '../services/odoo_service.dart';
import '../models/leave_request.dart';
import '../models/leave_type.dart';

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

  // إلغاء الطلب
  Future<void> _cancelRequest() async {
    // تأكيد الإلغاء
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('تأكيد الإلغاء'),
        content: Text('هل أنت متأكد من رغبتك في إلغاء طلب الإجازة هذا؟'),
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

    if (confirmed != true) return;

    try {
      setState(() {
        isLoading = true;
      });

      final result = await _leaveService.cancelLeaveRequest(currentRequest.id);

      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? 'تم إلغاء الطلب بنجاح'),
            backgroundColor: result['offline'] == true ? Colors.orange : Colors.green,
          ),
        );

        // العودة مع إشارة التحديث
        Navigator.of(context).pop(true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['error'] ?? 'فشل في إلغاء الطلب'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('خطأ: $e'),
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
      body: SafeArea(
        child: Column(
          children: [
            _buildAppBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(16),
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
                    SizedBox(height: 80), // مساحة للأزرار السفلية
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
              'تفاصيل طلب الإجازة',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.share, color: Colors.grey),
            onPressed: () {
              // يمكن إضافة وظيفة مشاركة لاحقاً
            },
          ),
        ],
      ),
    );
  }

  // بطاقة الحالة
  Widget _buildStatusCard() {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(int.parse('0xFF${currentRequest.stateColor.substring(1)}')),
            Color(int.parse('0xFF${currentRequest.stateColor.substring(1)}')).withOpacity(0.8),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Color(int.parse('0xFF${currentRequest.stateColor.substring(1)}')).withOpacity(0.3),
            blurRadius: 8,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            currentRequest.stateIcon,
            style: TextStyle(fontSize: 48),
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
              fontSize: 16,
              color: Colors.white.withOpacity(0.9),
            ),
          ),
          SizedBox(height: 12),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              currentRequest.formattedDuration,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // بطاقة التفاصيل
  Widget _buildDetailsCard() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'تفاصيل الإجازة',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 16),

          _buildDetailRow(
            icon: Icons.category,
            label: 'نوع الإجازة',
            value: currentRequest.leaveTypeName,
          ),
          _buildDetailRow(
            icon: Icons.calendar_today,
            label: 'تاريخ البداية',
            value: DateFormat('EEEE، d MMMM yyyy', 'ar').format(currentRequest.startDate),
          ),
          _buildDetailRow(
            icon: Icons.event,
            label: 'تاريخ النهاية',
            value: DateFormat('EEEE، d MMMM yyyy', 'ar').format(currentRequest.endDate),
          ),
          _buildDetailRow(
            icon: Icons.access_time,
            label: 'عدد الأيام',
            value: currentRequest.formattedDuration,
          ),

          if (currentRequest.reason.isNotEmpty)
            _buildDetailRow(
              icon: Icons.description,
              label: 'السبب',
              value: currentRequest.reason,
              isMultiLine: true,
            ),

          _buildDetailRow(
            icon: Icons.person,
            label: 'الموظف',
            value: currentRequest.employeeName ?? 'غير محدد',
          ),
          _buildDetailRow(
            icon: Icons.pending_actions,
            label: 'تاريخ الطلب',
            value: DateFormat('d MMMM yyyy - hh:mm a', 'ar').format(currentRequest.requestDate),
          ),

          if (currentRequest.approvalDate != null)
            _buildDetailRow(
              icon: Icons.check_circle,
              label: 'تاريخ الموافقة',
              value: DateFormat('d MMMM yyyy - hh:mm a', 'ar').format(currentRequest.approvalDate!),
            ),

          if (currentRequest.approverName != null)
            _buildDetailRow(
              icon: Icons.supervisor_account,
              label: 'المعتمد من',
              value: currentRequest.approverName!,
            ),
        ],
      ),
    );
  }

  // صف التفاصيل
  Widget _buildDetailRow({
    required IconData icon,
    required String label,
    required String value,
    bool isMultiLine = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: isMultiLine ? CrossAxisAlignment.start : CrossAxisAlignment.center,
        children: [
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 20, color: Colors.grey[600]),
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
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // بطاقة الخط الزمني
  Widget _buildTimelineCard() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'الخط الزمني',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 16),

          _buildTimelineItem(
            icon: Icons.add_circle,
            title: 'تم إنشاء الطلب',
            subtitle: DateFormat('d MMMM yyyy - hh:mm a', 'ar').format(currentRequest.requestDate),
            isCompleted: true,
          ),

          if (currentRequest.state != LeaveRequestState.draft)
            _buildTimelineItem(
              icon: Icons.send,
              title: 'تم إرسال الطلب للمراجعة',
              subtitle: 'في انتظار موافقة المدير',
              isCompleted: true,
            ),

          if (currentRequest.state == LeaveRequestState.validate1)
            _buildTimelineItem(
              icon: Icons.visibility,
              title: 'تحت المراجعة',
              subtitle: 'المدير يراجع الطلب حالياً',
              isCompleted: true,
              isActive: true,
            ),

          if (currentRequest.state == LeaveRequestState.validate)
            _buildTimelineItem(
              icon: Icons.check_circle,
              title: 'تمت الموافقة على الطلب',
              subtitle: currentRequest.approvalDate != null
                  ? DateFormat('d MMMM yyyy - hh:mm a', 'ar').format(currentRequest.approvalDate!)
                  : 'موافق عليه',
              isCompleted: true,
            ),

          if (currentRequest.state == LeaveRequestState.refuse)
            _buildTimelineItem(
              icon: Icons.cancel,
              title: 'تم رفض الطلب',
              subtitle: currentRequest.managerComment ?? 'تم رفض الطلب من قبل المدير',
              isCompleted: true,
              isRejected: true,
            ),

          if (currentRequest.state == LeaveRequestState.cancel)
            _buildTimelineItem(
              icon: Icons.block,
              title: 'تم إلغاء الطلب',
              subtitle: 'تم إلغاء الطلب من قبل الموظف',
              isCompleted: true,
              isRejected: true,
            ),
        ],
      ),
    );
  }

  // عنصر في الخط الزمني
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
    } else if (isCompleted) {
      color = Colors.green;
    } else if (isActive) {
      color = Colors.orange;
    } else {
      color = Colors.grey;
    }

    return Padding(
      padding: EdgeInsets.only(bottom: 16),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 2),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: isActive ? color : Colors.black,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 12,
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

  // بطاقة التعليقات
  Widget _buildCommentsCard() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.comment, color: Colors.blue),
              SizedBox(width: 8),
              Text(
                'تعليقات المدير',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.withOpacity(0.3)),
            ),
            child: Text(
              currentRequest.managerComment!,
              style: TextStyle(
                fontSize: 14,
                color: Colors.blue[800],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // الأزرار السفلية
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
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          if (currentRequest.canEdit) ...[
            Expanded(
              child: OutlinedButton(
                onPressed: isLoading ? null : () {
                  // يمكن إضافة وظيفة التعديل لاحقاً
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('وظيفة التعديل ستتوفر قريباً')),
                  );
                },
                style: OutlinedButton.styleFrom(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                child: Text(
                  'تعديل',
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
                  'إلغاء الطلب',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ),
        ],
      ),
    );
  }
}