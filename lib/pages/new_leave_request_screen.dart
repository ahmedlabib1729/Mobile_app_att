// pages/new_leave_request_screen.dart - صفحة إنشاء طلب إجازة جديد
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/leave_request.dart';
import '../models/employee.dart';
import '../services/leave_service.dart';
import '../services/odoo_service.dart';
import '../models/leave_type.dart';

class NewLeaveRequestScreen extends StatefulWidget {
  final OdooService odooService;
  final Employee employee;

  const NewLeaveRequestScreen({
    Key? key,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _NewLeaveRequestScreenState createState() => _NewLeaveRequestScreenState();
}

class _NewLeaveRequestScreenState extends State<NewLeaveRequestScreen> {
  final _formKey = GlobalKey<FormState>();
  final _reasonController = TextEditingController();

  late LeaveService _leaveService;

  // بيانات النموذج
  List<LeaveType> leaveTypes = [];
  LeaveType? selectedLeaveType;
  DateTime? startDate;
  DateTime? endDate;
  int calculatedDays = 0;

  // حالة التحميل
  bool isLoading = true;
  bool isSubmitting = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _leaveService = LeaveService(widget.odooService);
    _loadLeaveTypes();
  }

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  // تحميل أنواع الإجازات
  Future<void> _loadLeaveTypes() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      final types = await _leaveService.getLeaveTypes();

      setState(() {
        leaveTypes = types;
        if (types.isNotEmpty) {
          selectedLeaveType = types.first;
        }
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  // حساب عدد الأيام
  void _calculateDays() {
    if (startDate != null && endDate != null) {
      final difference = endDate!.difference(startDate!);
      setState(() {
        calculatedDays = difference.inDays + 1;
      });
    } else {
      setState(() {
        calculatedDays = 0;
      });
    }
  }

  // اختيار تاريخ البداية
  Future<void> _selectStartDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: startDate ?? DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(Duration(days: 365)),
      locale: Locale('ar'),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Colors.blue,
              onPrimary: Colors.white,
              onSurface: Colors.black,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null) {
      setState(() {
        startDate = picked;
        // إذا كان تاريخ النهاية قبل تاريخ البداية، قم بإعادة تعيينه
        if (endDate != null && endDate!.isBefore(picked)) {
          endDate = null;
        }
      });
      _calculateDays();
    }
  }

  // اختيار تاريخ النهاية
  Future<void> _selectEndDate() async {
    if (startDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('يرجى اختيار تاريخ البداية أولاً')),
      );
      return;
    }

    final picked = await showDatePicker(
      context: context,
      initialDate: endDate ?? startDate!,
      firstDate: startDate!,
      lastDate: DateTime.now().add(Duration(days: 365)),
      locale: Locale('ar'),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Colors.blue,
              onPrimary: Colors.white,
              onSurface: Colors.black,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null) {
      setState(() {
        endDate = picked;
      });
      _calculateDays();
    }
  }

  // إرسال الطلب
  Future<void> _submitRequest() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (selectedLeaveType == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('يرجى اختيار نوع الإجازة')),
      );
      return;
    }

    if (startDate == null || endDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('يرجى اختيار تواريخ الإجازة')),
      );
      return;
    }

    try {
      setState(() {
        isSubmitting = true;
      });

      // التحقق من توفر الإجازة أولاً
      final availability = await _leaveService.checkLeaveAvailability(
        employeeId: widget.employee.id,
        leaveTypeId: selectedLeaveType!.id,
        startDate: startDate!,
        endDate: endDate!,
      );

      if (!availability['available'] && availability['offline'] != true) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(availability['message'] ?? 'الإجازة غير متاحة'),
            backgroundColor: Colors.orange,
          ),
        );
        setState(() {
          isSubmitting = false;
        });
        return;
      }

      // إنشاء الطلب
      final result = await _leaveService.createLeaveRequest(
        employeeId: widget.employee.id,
        leaveTypeId: selectedLeaveType!.id,
        startDate: startDate!,
        endDate: endDate!,
        reason: _reasonController.text.trim(),
      );

      if (result['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? 'تم إنشاء طلب الإجازة بنجاح'),
            backgroundColor: result['offline'] == true ? Colors.orange : Colors.green,
          ),
        );

        // العودة إلى الصفحة السابقة مع إشارة النجاح
        Navigator.of(context).pop(true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['error'] ?? 'فشل في إنشاء طلب الإجازة'),
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
        isSubmitting = false;
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
              child: isLoading ? _buildLoadingState() : _buildForm(),
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
              'طلب إجازة جديد',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          SizedBox(width: 48), // لموازنة زر الرجوع
        ],
      ),
    );
  }

  // حالة التحميل
  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('جاري تحميل أنواع الإجازات...'),
        ],
      ),
    );
  }

  // النموذج الرئيسي
  Widget _buildForm() {
    if (errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red),
            SizedBox(height: 16),
            Text('خطأ في تحميل البيانات'),
            SizedBox(height: 8),
            Text(errorMessage!),
            SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadLeaveTypes,
              child: Text('إعادة المحاولة'),
            ),
          ],
        ),
      );
    }

    return Form(
      key: _formKey,
      child: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildLeaveTypeSection(),
                  SizedBox(height: 24),
                  _buildDateSection(),
                  SizedBox(height: 24),
                  _buildReasonSection(),
                  SizedBox(height: 24),
                  _buildSummarySection(),
                ],
              ),
            ),
          ),
          _buildBottomSection(),
        ],
      ),
    );
  }

  // قسم نوع الإجازة
  Widget _buildLeaveTypeSection() {
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
            'نوع الإجازة',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 12),

          if (leaveTypes.isEmpty)
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text('لا توجد أنواع إجازات متاحة'),
            )
          else
            ...leaveTypes.map((type) => _buildLeaveTypeOption(type)).toList(),
        ],
      ),
    );
  }

  // خيار نوع الإجازة
  Widget _buildLeaveTypeOption(LeaveType type) {
    final isSelected = selectedLeaveType?.id == type.id;

    return GestureDetector(
      onTap: () {
        setState(() {
          selectedLeaveType = type;
        });
      },
      child: Container(
        margin: EdgeInsets.only(bottom: 8),
        padding: EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSelected ? Color(int.parse('0xFF${type.color.substring(1)}')).withOpacity(0.1) : Colors.grey[50],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? Color(int.parse('0xFF${type.color.substring(1)}')) : Colors.grey[300]!,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isSelected ? Color(int.parse('0xFF${type.color.substring(1)}')) : Colors.transparent,
                border: Border.all(
                  color: Color(int.parse('0xFF${type.color.substring(1)}')),
                  width: 2,
                ),
              ),
              child: isSelected
                  ? Icon(Icons.check, size: 14, color: Colors.white)
                  : null,
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    type.name,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    'حد أقصى: ${type.maxDays} يوم',
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
      ),
    );
  }

  // قسم التواريخ
  Widget _buildDateSection() {
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
            'فترة الإجازة',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 16),

          Row(
            children: [
              Expanded(
                child: _buildDateField(
                  label: 'تاريخ البداية',
                  date: startDate,
                  onTap: _selectStartDate,
                ),
              ),
              SizedBox(width: 16),
              Expanded(
                child: _buildDateField(
                  label: 'تاريخ النهاية',
                  date: endDate,
                  onTap: _selectEndDate,
                ),
              ),
            ],
          ),

          if (calculatedDays > 0) ...[
            SizedBox(height: 16),
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.calendar_today, color: Colors.blue, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'عدد الأيام: $calculatedDays ${calculatedDays == 1 ? "يوم" : calculatedDays == 2 ? "يومان" : "أيام"}',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // حقل التاريخ
  Widget _buildDateField({
    required String label,
    required DateTime? date,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey[300]!),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
            SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.calendar_today, size: 16, color: Colors.grey),
                SizedBox(width: 8),
                Text(
                  date != null
                      ? DateFormat('d MMMM yyyy', 'ar').format(date)
                      : 'اختر التاريخ',
                  style: TextStyle(
                    fontSize: 14,
                    color: date != null ? Colors.black : Colors.grey,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // قسم سبب الإجازة
  Widget _buildReasonSection() {
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
            'سبب الإجازة',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 12),
          TextFormField(
            controller: _reasonController,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: 'اكتب سبب طلب الإجازة (اختياري)',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              filled: true,
              fillColor: Colors.grey[50],
            ),
            validator: (value) {
              // السبب اختياري
              return null;
            },
          ),
        ],
      ),
    );
  }

  // قسم الملخص
  Widget _buildSummarySection() {
    if (selectedLeaveType == null || startDate == null || endDate == null) {
      return SizedBox.shrink();
    }

    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.green.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.summarize, color: Colors.green),
              SizedBox(width: 8),
              Text(
                'ملخص الطلب',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.green,
                ),
              ),
            ],
          ),
          SizedBox(height: 12),

          _buildSummaryRow('نوع الإجازة:', selectedLeaveType!.name),
          _buildSummaryRow('من:', DateFormat('d MMMM yyyy', 'ar').format(startDate!)),
          _buildSummaryRow('إلى:', DateFormat('d MMMM yyyy', 'ar').format(endDate!)),
          _buildSummaryRow('المدة:', '$calculatedDays ${calculatedDays == 1 ? "يوم" : calculatedDays == 2 ? "يومان" : "أيام"}'),

          if (_reasonController.text.trim().isNotEmpty)
            _buildSummaryRow('السبب:', _reasonController.text.trim()),
        ],
      ),
    );
  }

  // صف في الملخص
  Widget _buildSummaryRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: Colors.green[700],
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 12,
                color: Colors.green[700],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // القسم السفلي مع الأزرار
  Widget _buildBottomSection() {
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
          Expanded(
            child: OutlinedButton(
              onPressed: isSubmitting ? null : () => Navigator.of(context).pop(),
              style: OutlinedButton.styleFrom(
                padding: EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: Text(
                'إلغاء',
                style: TextStyle(fontSize: 16),
              ),
            ),
          ),
          SizedBox(width: 16),
          Expanded(
            flex: 2,
            child: ElevatedButton(
              onPressed: isSubmitting ? null : _submitRequest,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
                padding: EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: isSubmitting
                  ? SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
                  : Text(
                'إرسال الطلب',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    );
  }
}