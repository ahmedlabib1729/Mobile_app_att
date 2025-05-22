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
          ? Center(child: Text(_errorMessage!))
          : _employee == null
          ? const Center(child: Text('لا توجد بيانات متاحة'))
          : _buildProfileContent(),
    );
  }

  Widget _buildProfileContent() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // بطاقة المعلومات الشخصية
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const CircleAvatar(
                      radius: 60,
                      backgroundColor: Colors.blue,
                      child: Icon(
                        Icons.person,
                        size: 60,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _employee!.name,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _employee!.jobTitle,
                      style: TextStyle(
                        fontSize: 18,
                        color: Colors.blue.shade700,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 4),
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
            ),

            const SizedBox(height: 16),

            // بطاقة معلومات العمل
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'معلومات العمل',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    _buildProfileField('رقم الموظف', _employee!.id.toString()),
                    const Divider(),
                    _buildProfileField('المسمى الوظيفي', _employee!.jobTitle),
                    const Divider(),
                    _buildProfileField('القسم', _employee!.department),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // هنا يمكنك إضافة المزيد من البطاقات لعرض معلومات إضافية
            // مثل معلومات الاتصال أو معلومات الإجازات أو غيرها
          ],
        ),
      ),
    );
  }

  Widget _buildProfileField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 16,
              color: Colors.grey,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}