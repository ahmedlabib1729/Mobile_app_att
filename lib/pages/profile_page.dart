// lib/pages/profile_page.dart - نسخة بسيطة بدون مكتبات خارجية
import 'package:flutter/material.dart';
import '../models/employee.dart';
import '../services/odoo_service.dart';

class ProfilePage extends StatefulWidget {
  final OdooService odooService;
  final Employee? initialEmployee;

  const ProfilePage({
    Key? key,
    required this.odooService,
    this.initialEmployee,
  }) : super(key: key);

  @override
  _ProfilePageState createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _isLoading = true;
  Employee? _employee;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    // إذا تم تمرير بيانات موظف أولية، استخدمها وتخطى التحميل
    if (widget.initialEmployee != null) {
      _employee = widget.initialEmployee;
      _isLoading = false;
    } else {
      _loadEmployeeData();
    }
  }

  // تحميل بيانات الموظف من Odoo
  Future<void> _loadEmployeeData() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final employee = await widget.odooService.getCurrentEmployee();

      setState(() {
        _employee = employee;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'تعذر تحميل بيانات الموظف: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الملف الشخصي'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadEmployeeData,
            tooltip: 'تحديث البيانات',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
          ? _buildErrorWidget()
          : _employee == null
          ? const Center(child: Text('لا توجد بيانات متاحة'))
          : _buildProfileContent(),
    );
  }

  // ويدجت عرض الخطأ
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
              _errorMessage!,
              style: TextStyle(fontSize: 16),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _loadEmployeeData,
              child: Text('إعادة المحاولة'),
            ),
          ],
        ),
      ),
    );
  }

  // محتوى الملف الشخصي
  Widget _buildProfileContent() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // بطاقة المعلومات الشخصية
            _buildProfileCard(),

            const SizedBox(height: 16),

            // بطاقة معلومات العمل
            _buildWorkInfoCard(),

            const SizedBox(height: 16),

            // بطاقة معلومات الاتصال
            _buildContactInfoCard(),
          ],
        ),
      ),
    );
  }

  // بطاقة المعلومات الشخصية
  Widget _buildProfileCard() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            // صورة الموظف (بسيطة)
            CircleAvatar(
              radius: 60,
              backgroundColor: Colors.blue,
              backgroundImage: _employee!.hasImage
                  ? NetworkImage(_employee!.bestAvailableImage!)
                  : null,
              child: !_employee!.hasImage
                  ? Icon(Icons.person, size: 60, color: Colors.white)
                  : null,
            ),

            const SizedBox(height: 16),

            // اسم الموظف
            Text(
              _employee!.name,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 8),

            // المسمى الوظيفي
            Text(
              _employee!.jobTitle,
              style: TextStyle(
                fontSize: 18,
                color: Colors.blue.shade700,
              ),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 4),

            // القسم
            Text(
              _employee!.department,
              style: const TextStyle(
                fontSize: 16,
                color: Colors.grey,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  // بطاقة معلومات العمل
  Widget _buildWorkInfoCard() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.work, color: Colors.blue),
                SizedBox(width: 8),
                Text(
                  'معلومات العمل',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _buildProfileField('رقم الموظف', _employee!.id.toString(), Icons.badge),
            const Divider(),
            _buildProfileField('المسمى الوظيفي', _employee!.jobTitle, Icons.work_outline),
            const Divider(),
            _buildProfileField('القسم', _employee!.department, Icons.business),
          ],
        ),
      ),
    );
  }

  // بطاقة معلومات الاتصال
  Widget _buildContactInfoCard() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.contact_phone, color: Colors.green),
                SizedBox(width: 8),
                Text(
                  'معلومات الاتصال',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_employee!.workEmail.isNotEmpty)
              _buildProfileField('البريد الإلكتروني', _employee!.workEmail, Icons.email),
            if (_employee!.workEmail.isNotEmpty && (_employee!.workPhone.isNotEmpty || _employee!.mobilePhone.isNotEmpty))
              const Divider(),
            if (_employee!.workPhone.isNotEmpty)
              _buildProfileField('هاتف العمل', _employee!.workPhone, Icons.phone),
            if (_employee!.workPhone.isNotEmpty && _employee!.mobilePhone.isNotEmpty)
              const Divider(),
            if (_employee!.mobilePhone.isNotEmpty)
              _buildProfileField('الهاتف المحمول', _employee!.mobilePhone, Icons.smartphone),
          ],
        ),
      ),
    );
  }

  // حقل معلومات الملف الشخصي
  Widget _buildProfileField(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
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
                  style: const TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 16,
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
}