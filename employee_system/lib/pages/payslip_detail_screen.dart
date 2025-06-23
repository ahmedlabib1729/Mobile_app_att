// lib/pages/payslip_detail_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'dart:io';
import 'dart:ui' as ui;
import 'dart:typed_data';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:flutter/rendering.dart';
import '../models/payslip.dart';
import '../services/odoo_service.dart';
import '../services/language_manager.dart';

class PayslipDetailScreen extends StatefulWidget {
  final OdooService odooService;
  final int payslipId;

  const PayslipDetailScreen({
    Key? key,
    required this.odooService,
    required this.payslipId,
  }) : super(key: key);

  @override
  _PayslipDetailScreenState createState() => _PayslipDetailScreenState();
}

class _PayslipDetailScreenState extends State<PayslipDetailScreen> {
  Payslip? payslip;
  bool isLoading = true;
  String errorMessage = '';
  bool isDownloading = false;

  // للحصول على صورة من الصفحة
  GlobalKey _repaintBoundaryKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _loadPayslipDetails();
  }

  Future<void> _loadPayslipDetails() async {
    setState(() {
      isLoading = true;
      errorMessage = '';
    });

    try {
      final details = await widget.odooService.getPayslipDetails(widget.payslipId);

      setState(() {
        payslip = details;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  // خيارات التحميل والمشاركة
  void _showDownloadOptions() {
    showModalBottomSheet(
      context: context,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        final lang = context.lang;
        return Container(
          padding: EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 40,
                height: 4,
                margin: EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Text(
                lang.translate('share_options'),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 20),
              // حفظ كصورة
              ListTile(
                leading: Container(
                  padding: EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Color(0xFF2196F3).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.image, color: Color(0xFF2196F3)),
                ),
                title: Text(lang.translate('save_as_image')),
                subtitle: Text(lang.translate('save_payslip_image')),
                onTap: () {
                  Navigator.pop(context);
                  _captureAndSaveImage();
                },
              ),
              // نسخ التفاصيل
              ListTile(
                leading: Container(
                  padding: EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.green.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.copy, color: Colors.green),
                ),
                title: Text(lang.translate('copy_details')),
                subtitle: Text(lang.translate('copy_to_clipboard')),
                onTap: () {
                  Navigator.pop(context);
                  _copyDetailsToClipboard();
                },
              ),
              // تحميل PDF (إن وجد)
              ListTile(
                leading: Container(
                  padding: EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.picture_as_pdf, color: Colors.orange),
                ),
                title: Text(lang.translate('download_pdf')),
                subtitle: Text(lang.translate('original_document')),
                onTap: () {
                  Navigator.pop(context);
                  _downloadPdf();
                },
              ),
            ],
          ),
        );
      },
    );
  }

  // حفظ الصفحة كصورة
  Future<void> _captureAndSaveImage() async {
    try {
      setState(() => isDownloading = true);

      RenderRepaintBoundary? boundary = _repaintBoundaryKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) throw Exception('Could not capture image');

      ui.Image image = await boundary.toImage(pixelRatio: 3.0);
      ByteData? byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData == null) throw Exception('Could not convert image');

      Uint8List pngBytes = byteData.buffer.asUint8List();

      final tempDir = await getTemporaryDirectory();
      final file = File('${tempDir.path}/payslip_${payslip!.number}.png');
      await file.writeAsBytes(pngBytes);

      await Share.shareXFiles(
        [XFile(file.path)],
        subject: 'كشف مرتب ${payslip!.periodText}',
      );

      _showSnackBar(context.lang.translate('image_saved'));
    } catch (e) {
      _showSnackBar('${context.lang.translate('error')}: $e', isError: true);
    } finally {
      setState(() => isDownloading = false);
    }
  }

  // نسخ التفاصيل للحافظة
  void _copyDetailsToClipboard() {
    final lang = context.lang;
    final formatter = NumberFormat('#,###');

    String details = '''
${lang.translate('payslip')} - ${payslip!.periodText}
${'-' * 40}
${lang.translate('employee')}: ${payslip!.employeeName}
${lang.translate('period')}: ${DateFormat('dd/MM/yyyy').format(payslip!.dateFrom)} - ${DateFormat('dd/MM/yyyy').format(payslip!.dateTo)}
${lang.translate('status')}: ${lang.translate(payslip!.state)}

${lang.translate('salary_details')}:
${'-' * 20}
${lang.translate('basic_salary')}: ${formatter.format(payslip!.basicSalary)} ${payslip!.currency}
${lang.translate('allowances')}: ${formatter.format(payslip!.totalAllowances)} ${payslip!.currency}
${lang.translate('gross_salary')}: ${formatter.format(payslip!.grossSalary)} ${payslip!.currency}
${lang.translate('deductions')}: ${formatter.format(payslip!.totalDeductions)} ${payslip!.currency}
${'-' * 20}
${lang.translate('net_salary')}: ${formatter.format(payslip!.netSalary)} ${payslip!.currency}
''';

    // إضافة تفاصيل البدلات
    if (payslip!.housingAllowance > 0 || payslip!.transportationAllowance > 0) {
      details += '\n${lang.translate('allowances_details')}:\n';
      if (payslip!.housingAllowance > 0) {
        details += '- ${lang.translate('housing_allowance')}: ${formatter.format(payslip!.housingAllowance)} ${payslip!.currency}\n';
      }
      if (payslip!.transportationAllowance > 0) {
        details += '- ${lang.translate('transportation_allowance')}: ${formatter.format(payslip!.transportationAllowance)} ${payslip!.currency}\n';
      }
      if (payslip!.foodAllowance > 0) {
        details += '- ${lang.translate('food_allowance')}: ${formatter.format(payslip!.foodAllowance)} ${payslip!.currency}\n';
      }
    }

    // إضافة تفاصيل الخصومات
    if (payslip!.socialInsurance > 0 || payslip!.taxes > 0) {
      details += '\n${lang.translate('deductions_details')}:\n';
      if (payslip!.socialInsurance > 0) {
        details += '- ${lang.translate('social_insurance')}: ${formatter.format(payslip!.socialInsurance)} ${payslip!.currency}\n';
      }
      if (payslip!.taxes > 0) {
        details += '- ${lang.translate('taxes')}: ${formatter.format(payslip!.taxes)} ${payslip!.currency}\n';
      }
    }

    Clipboard.setData(ClipboardData(text: details));
    _showSnackBar(lang.translate('copied_to_clipboard'));
  }

  Future<void> _downloadPdf() async {
    if (isDownloading) return;

    setState(() {
      isDownloading = true;
    });

    try {
      final pdfBytes = await widget.odooService.downloadPayslipPdf(widget.payslipId);

      if (pdfBytes != null) {
        final tempDir = await getTemporaryDirectory();
        final file = File('${tempDir.path}/payslip_${payslip!.number}.pdf');
        await file.writeAsBytes(pdfBytes);

        await Share.shareXFiles(
          [XFile(file.path)],
          subject: 'كشف مرتب ${payslip!.periodText}',
        );
      } else {
        _showSnackBar(context.lang.translate('download_failed'), isError: true);
      }
    } catch (e) {
      _showSnackBar('${context.lang.translate('pdf_error_try_image')}', isError: true);
    } finally {
      setState(() {
        isDownloading = false;
      });
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red : Colors.green,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final lang = context.lang;

    return Scaffold(
      backgroundColor: Color(0xFFF8F9FD),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: Text(
          lang.translate('payslip_details'),
          style: TextStyle(
            color: Color(0xFF1A1A1A),
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios, color: Color(0xFF1A1A1A)),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          if (payslip != null)
            IconButton(
              icon: isDownloading
                  ? SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF2196F3)),
                ),
              )
                  : Icon(Icons.share, color: Color(0xFF2196F3)),
              onPressed: _showDownloadOptions,
            ),
        ],
      ),
      body: isLoading
          ? Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF2196F3)),
            ),
            SizedBox(height: 16),
            Text(
              lang.translate('loading'),
              style: TextStyle(color: Colors.grey[600]),
            ),
          ],
        ),
      )
          : errorMessage.isNotEmpty
          ? Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red),
            SizedBox(height: 16),
            Text(
              lang.translate('error'),
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Text(errorMessage),
            SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadPayslipDetails,
              icon: Icon(Icons.refresh),
              label: Text(lang.translate('retry')),
            ),
          ],
        ),
      )
          : payslip == null
          ? Center(
        child: Text(
          lang.translate('no_data'),
          style: TextStyle(fontSize: 16, color: Colors.grey[600]),
        ),
      )
          : SingleChildScrollView(
        child: RepaintBoundary(
          key: _repaintBoundaryKey,
          child: Container(
            color: Color(0xFFF8F9FD),
            padding: EdgeInsets.all(16),
            child: Column(
              children: [
                _buildCompanyHeader(),
                SizedBox(height: 16),
                _buildHeaderCard(),
                SizedBox(height: 16),
                _buildSalaryBreakdown(),
                SizedBox(height: 16),
                _buildAllowancesCard(),
                SizedBox(height: 16),
                _buildDeductionsCard(),
                SizedBox(height: 16),
                _buildNetSalaryCard(),
                if (payslip!.notes != null && payslip!.notes!.isNotEmpty) ...[
                  SizedBox(height: 16),
                  _buildNotesCard(),
                ],
                SizedBox(height: 16),
                _buildFooter(),
                SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // إضافة هيدر الشركة
  Widget _buildCompanyHeader() {
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
        children: [
          if (payslip!.companyLogo != null)
            Image.network(
              payslip!.companyLogo!,
              height: 60,
              errorBuilder: (context, error, stackTrace) => Icon(
                Icons.business,
                size: 60,
                color: Colors.grey[400],
              ),
            )
          else
            Icon(
              Icons.business,
              size: 60,
              color: Color(0xFF2196F3),
            ),
          SizedBox(height: 12),
          Text(
            payslip!.companyName ?? 'الشركة',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1A1A1A),
            ),
          ),
          SizedBox(height: 8),
          Text(
            'كشف مرتب',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderCard() {
    final lang = context.lang;
    final formatter = DateFormat('dd/MM/yyyy');

    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF2196F3),
            Color(0xFF1976D2),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Color(0xFF2196F3).withOpacity(0.3),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    lang.translate('payslip'),
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 14,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    payslip!.periodText,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  children: [
                    Text(
                      payslip!.stateIcon,
                      style: TextStyle(fontSize: 16),
                    ),
                    SizedBox(width: 6),
                    Text(
                      lang.translate(payslip!.state),
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: 20),
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                _buildInfoRow(
                  lang.translate('employee'),
                  payslip!.employeeName,
                  Icons.person,
                ),
                SizedBox(height: 12),
                _buildInfoRow(
                  lang.translate('employee_id'),
                  '#${payslip!.employeeId}',
                  Icons.badge,
                ),
                SizedBox(height: 12),
                _buildInfoRow(
                  lang.translate('period'),
                  '${formatter.format(payslip!.dateFrom)} - ${formatter.format(payslip!.dateTo)}',
                  Icons.date_range,
                ),
                SizedBox(height: 12),
                _buildInfoRow(
                  lang.translate('working_days'),
                  '${payslip!.actualWorkingDays} / ${payslip!.workingDays}',
                  Icons.calendar_month,
                ),
                if (payslip!.paymentDate.isNotEmpty) ...[
                  SizedBox(height: 12),
                  _buildInfoRow(
                    lang.translate('payment_date'),
                    payslip!.paymentDate,
                    Icons.payment,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: Colors.white70, size: 20),
        SizedBox(width: 8),
        Text(
          '$label:',
          style: TextStyle(color: Colors.white70, fontSize: 14),
        ),
        SizedBox(width: 8),
        Expanded(
          child: Text(
            value,
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.end,
          ),
        ),
      ],
    );
  }

  Widget _buildSalaryBreakdown() {
    final lang = context.lang;
    final formatter = NumberFormat('#,###');

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
                  Icons.account_balance_wallet,
                  color: Color(0xFF2196F3),
                  size: 20,
                ),
              ),
              SizedBox(width: 12),
              Text(
                lang.translate('salary_breakdown'),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A1A),
                ),
              ),
            ],
          ),
          SizedBox(height: 20),
          _buildSalaryRow(
            lang.translate('basic_salary'),
            formatter.format(payslip!.basicSalary),
            payslip!.currency,
          ),
          SizedBox(height: 12),
          _buildSalaryRow(
            lang.translate('total_allowances'),
            formatter.format(payslip!.totalAllowances),
            payslip!.currency,
            color: Color(0xFF4CAF50),
            prefix: '+',
          ),
          Divider(height: 24),
          _buildSalaryRow(
            lang.translate('gross_salary'),
            formatter.format(payslip!.grossSalary),
            payslip!.currency,
            isBold: true,
          ),
          SizedBox(height: 12),
          _buildSalaryRow(
            lang.translate('total_deductions'),
            formatter.format(payslip!.totalDeductions),
            payslip!.currency,
            color: Color(0xFFF44336),
            prefix: '-',
          ),
        ],
      ),
    );
  }

  Widget _buildSalaryRow(String label, String amount, String currency, {
    Color? color,
    bool isBold = false,
    String prefix = '',
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 14,
            color: Colors.grey[700],
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        Text(
          '$prefix$amount $currency',
          style: TextStyle(
            fontSize: 16,
            color: color ?? Color(0xFF1A1A1A),
            fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildAllowancesCard() {
    final lang = context.lang;
    final formatter = NumberFormat('#,###');

    final allowances = [
      if (payslip!.housingAllowance > 0)
        {'label': lang.translate('housing_allowance'), 'amount': payslip!.housingAllowance},
      if (payslip!.transportationAllowance > 0)
        {'label': lang.translate('transportation_allowance'), 'amount': payslip!.transportationAllowance},
      if (payslip!.foodAllowance > 0)
        {'label': lang.translate('food_allowance'), 'amount': payslip!.foodAllowance},
      if (payslip!.phoneAllowance > 0)
        {'label': lang.translate('phone_allowance'), 'amount': payslip!.phoneAllowance},
      if (payslip!.otherAllowances > 0)
        {'label': lang.translate('other_allowances'), 'amount': payslip!.otherAllowances},
    ];

    if (allowances.isEmpty) return SizedBox.shrink();

    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Color(0xFF4CAF50).withOpacity(0.2),
          width: 1,
        ),
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
                  color: Color(0xFF4CAF50).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.add_circle_outline,
                  color: Color(0xFF4CAF50),
                  size: 20,
                ),
              ),
              SizedBox(width: 12),
              Text(
                lang.translate('allowances'),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A1A),
                ),
              ),
              Spacer(),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: Color(0xFF4CAF50).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${payslip!.allowancesPercentage.toStringAsFixed(1)}%',
                  style: TextStyle(
                    color: Color(0xFF4CAF50),
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 16),
          ...allowances.map((item) => Padding(
            padding: EdgeInsets.only(bottom: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  item['label'] as String,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey[700],
                  ),
                ),
                Text(
                  '${formatter.format(item['amount'])} ${payslip!.currency}',
                  style: TextStyle(
                    fontSize: 14,
                    color: Color(0xFF4CAF50),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          )).toList(),
          Divider(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                lang.translate('total'),
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[700],
                ),
              ),
              Text(
                '${formatter.format(payslip!.totalAllowances)} ${payslip!.currency}',
                style: TextStyle(
                  fontSize: 16,
                  color: Color(0xFF4CAF50),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDeductionsCard() {
    final lang = context.lang;
    final formatter = NumberFormat('#,###');

    final deductions = [
      if (payslip!.socialInsurance > 0)
        {'label': lang.translate('social_insurance'), 'amount': payslip!.socialInsurance},
      if (payslip!.taxes > 0)
        {'label': lang.translate('taxes'), 'amount': payslip!.taxes},
      if (payslip!.loans > 0)
        {'label': lang.translate('loans'), 'amount': payslip!.loans},
      if (payslip!.absence > 0)
        {'label': lang.translate('absence_deduction'), 'amount': payslip!.absence},
      if (payslip!.otherDeductions > 0)
        {'label': lang.translate('other_deductions'), 'amount': payslip!.otherDeductions},
    ];

    if (deductions.isEmpty) return SizedBox.shrink();

    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Color(0xFFF44336).withOpacity(0.2),
          width: 1,
        ),
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
                  color: Color(0xFFF44336).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.remove_circle_outline,
                  color: Color(0xFFF44336),
                  size: 20,
                ),
              ),
              SizedBox(width: 12),
              Text(
                lang.translate('deductions'),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A1A),
                ),
              ),
              Spacer(),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: Color(0xFFF44336).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${payslip!.deductionsPercentage.toStringAsFixed(1)}%',
                  style: TextStyle(
                    color: Color(0xFFF44336),
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 16),
          ...deductions.map((item) => Padding(
            padding: EdgeInsets.only(bottom: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  item['label'] as String,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey[700],
                  ),
                ),
                Text(
                  '${formatter.format(item['amount'])} ${payslip!.currency}',
                  style: TextStyle(
                    fontSize: 14,
                    color: Color(0xFFF44336),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          )).toList(),
          Divider(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                lang.translate('total'),
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[700],
                ),
              ),
              Text(
                '${formatter.format(payslip!.totalDeductions)} ${payslip!.currency}',
                style: TextStyle(
                  fontSize: 16,
                  color: Color(0xFFF44336),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNetSalaryCard() {
    final lang = context.lang;
    final formatter = NumberFormat('#,###');

    return Container(
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF2196F3),
            Color(0xFF1976D2),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Color(0xFF2196F3).withOpacity(0.3),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(
            Icons.account_balance_wallet,
            color: Colors.white,
            size: 48,
          ),
          SizedBox(height: 16),
          Text(
            lang.translate('net_salary'),
            style: TextStyle(
              color: Colors.white70,
              fontSize: 16,
            ),
          ),
          SizedBox(height: 8),
          Text(
            '${formatter.format(payslip!.netSalary)} ${payslip!.currency}',
            style: TextStyle(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (payslip!.bankName != null || payslip!.bankAccount != null) ...[
            SizedBox(height: 20),
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  if (payslip!.bankName != null)
                    _buildBankInfoRow(
                      lang.translate('bank'),
                      payslip!.bankName!,
                      Icons.account_balance,
                    ),
                  if (payslip!.bankAccount != null) ...[
                    if (payslip!.bankName != null) SizedBox(height: 8),
                    _buildBankInfoRow(
                      lang.translate('account'),
                      payslip!.bankAccount!,
                      Icons.credit_card,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBankInfoRow(String label, String value, IconData icon) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(icon, color: Colors.white70, size: 16),
        SizedBox(width: 8),
        Text(
          '$label: ',
          style: TextStyle(color: Colors.white70, fontSize: 14),
        ),
        Text(
          value,
          style: TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildNotesCard() {
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
                  color: Colors.orange.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.note,
                  color: Colors.orange,
                  size: 20,
                ),
              ),
              SizedBox(width: 12),
              Text(
                lang.translate('notes'),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A1A),
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          Text(
            payslip!.notes!,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[700],
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  // إضافة فوتر
  Widget _buildFooter() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(
            'تم إصدار هذا الكشف إلكترونياً',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
            ),
          ),
          SizedBox(height: 4),
          Text(
            DateFormat('dd/MM/yyyy - hh:mm a').format(DateTime.now()),
            style: TextStyle(
              fontSize: 11,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }
}