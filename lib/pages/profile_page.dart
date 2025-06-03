// lib/pages/profile_page.dart - Modern English Version
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
    if (widget.initialEmployee != null) {
      _employee = widget.initialEmployee;
      _isLoading = false;
    } else {
      _loadEmployeeData();
    }
  }

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
        _errorMessage = 'Failed to load employee data: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadEmployeeData,
            tooltip: 'Refresh',
          ),
        ],
        backgroundColor: Color(0xFF2196F3),
        elevation: 0,
      ),
      backgroundColor: const Color(0xFFF8F9FD),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
          ? _buildErrorWidget()
          : _employee == null
          ? const Center(child: Text('No data available'))
          : _buildProfileContent(),
    );
  }

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
              style: ElevatedButton.styleFrom(
                backgroundColor: Color(0xFF2196F3),
              ),
              child: Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileContent() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Profile card
            _buildProfileCard(),

            const SizedBox(height: 18),

            // Work info card
            _buildWorkInfoCard(),

            const SizedBox(height: 18),

            // Contact info card
            _buildContactInfoCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileCard() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(0xFFe3f2fd),
            Colors.white,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: Colors.blue.withOpacity(0.06),
            blurRadius: 20,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 20),
        child: Column(
          children: [
            // Employee image
            CircleAvatar(
              radius: 56,
              backgroundColor: Color(0xFF2196F3),
              backgroundImage: _employee!.hasImage
                  ? NetworkImage(_employee!.bestAvailableImage!)
                  : null,
              child: !_employee!.hasImage
                  ? Icon(Icons.person, size: 60, color: Colors.white)
                  : null,
            ),

            const SizedBox(height: 16),

            // Employee name
            Text(
              _employee!.name,
              style: const TextStyle(
                fontSize: 25,
                fontWeight: FontWeight.bold,
                color: Color(0xFF212121),
              ),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 8),

            // Job title
            Text(
              _employee!.jobTitle,
              style: TextStyle(
                fontSize: 17,
                color: Color(0xFF2196F3),
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 4),

            // Department
            Text(
              _employee!.department,
              style: const TextStyle(
                fontSize: 15,
                color: Colors.grey,
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkInfoCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
      ),
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(19.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.work, color: Color(0xFF2196F3)),
                SizedBox(width: 8),
                Text(
                  'Work Information',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF222B45),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 17),
            _buildProfileField('Employee ID', _employee!.id.toString(), Icons.badge),
            const Divider(),
            _buildProfileField('Job Title', _employee!.jobTitle, Icons.work_outline),
            const Divider(),
            _buildProfileField('Department', _employee!.department, Icons.business),
          ],
        ),
      ),
    );
  }

  Widget _buildContactInfoCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
      ),
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(19.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.contact_phone, color: Color(0xFF43A047)),
                SizedBox(width: 8),
                Text(
                  'Contact Information',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF222B45),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 17),
            if (_employee!.workEmail.isNotEmpty)
              _buildProfileField('Work Email', _employee!.workEmail, Icons.email),
            if (_employee!.workEmail.isNotEmpty && (_employee!.workPhone.isNotEmpty || _employee!.mobilePhone.isNotEmpty))
              const Divider(),
            if (_employee!.workPhone.isNotEmpty)
              _buildProfileField('Work Phone', _employee!.workPhone, Icons.phone),
            if (_employee!.workPhone.isNotEmpty && _employee!.mobilePhone.isNotEmpty)
              const Divider(),
            if (_employee!.mobilePhone.isNotEmpty)
              _buildProfileField('Mobile Phone', _employee!.mobilePhone, Icons.smartphone),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileField(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9.0),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(9),
            ),
            child: Icon(icon, size: 21, color: Colors.blueGrey),
          ),
          SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12.5,
                    color: Colors.grey,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 16.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF222B45),
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
