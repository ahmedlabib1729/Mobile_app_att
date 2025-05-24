// lib/pages/announcement_details_screen.dart - English & Modern UI
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/employee.dart';
import '../models/announcement.dart';
import '../services/odoo_service.dart';

class AnnouncementDetailsScreen extends StatefulWidget {
  final Announcement announcement;
  final OdooService odooService;
  final Employee employee;

  const AnnouncementDetailsScreen({
    Key? key,
    required this.announcement,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _AnnouncementDetailsScreenState createState() => _AnnouncementDetailsScreenState();
}

class _AnnouncementDetailsScreenState extends State<AnnouncementDetailsScreen> {
  Map<String, dynamic>? detailedAnnouncement;
  bool isLoading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _loadAnnouncementDetails();
  }

  Future<void> _loadAnnouncementDetails() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      final details = await widget.odooService.getAnnouncementDetail(
        widget.announcement.id,
        widget.employee.id,
      );

      setState(() {
        detailedAnnouncement = details;
        isLoading = false;
      });

      // Mark as read if not already
      if (!widget.announcement.isRead) {
        await widget.odooService.markAnnouncementAsRead(
          widget.announcement.id,
          widget.employee.id,
        );
      }
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  Future<void> _openAttachment(Map<String, dynamic> attachment) async {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Attachment link: http://192.168.64.132:8018${attachment['url']}'),
        duration: Duration(seconds: 5),
        action: SnackBarAction(
          label: 'Copy',
          onPressed: () {
            // Clipboard functionality can be added here
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFFF6F8FC),
      body: SafeArea(
        child: Column(
          children: [
            _buildAppBar(),
            Expanded(
              child: isLoading
                  ? Center(child: CircularProgressIndicator())
                  : errorMessage != null
                  ? _buildErrorWidget()
                  : _buildContent(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: Colors.white,
      child: Row(
        children: [
          IconButton(
            icon: Icon(Icons.arrow_back_ios, color: Colors.grey[700]),
            onPressed: () => Navigator.of(context).pop(),
          ),
          Expanded(
            child: Text(
              'Announcement Details',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Colors.blue[900],
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.share, color: Colors.grey),
            onPressed: () {
              // Add share functionality if needed
            },
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    final announcement = detailedAnnouncement ?? {};

    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInfoCard(announcement),
          SizedBox(height: 16),
          _buildContentCard(announcement),
          if (announcement['attachments'] != null && (announcement['attachments'] as List).isNotEmpty) ...[
            SizedBox(height: 16),
            _buildAttachmentsCard(announcement['attachments']),
          ],
          SizedBox(height: 16),
          _buildAdditionalInfo(announcement),
        ],
      ),
    );
  }

  Widget _buildInfoCard(Map<String, dynamic> announcement) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Color(int.parse(
                        '0xFF${widget.announcement.typeColor.substring(1)}')).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(widget.announcement.typeIcon, style: TextStyle(fontSize: 16)),
                      SizedBox(width: 4),
                      Text(
                        widget.announcement.typeText,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Color(int.parse('0xFF${widget.announcement.typeColor.substring(1)}')),
                        ),
                      ),
                    ],
                  ),
                ),
                Spacer(),
                if (widget.announcement.isPinned)
                  Icon(Icons.push_pin, size: 20, color: Colors.red),
                if (widget.announcement.priority == 'high' || widget.announcement.priority == 'urgent')
                  Padding(
                    padding: EdgeInsets.only(left: 8),
                    child: Text(
                      widget.announcement.priorityIcon,
                      style: TextStyle(fontSize: 24),
                    ),
                  ),
              ],
            ),
            SizedBox(height: 16),
            Text(
              announcement['title'] ?? widget.announcement.title,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.blueGrey[900],
              ),
            ),
            if (announcement['summary'] != null && announcement['summary'].toString().isNotEmpty) ...[
              SizedBox(height: 8),
              Text(
                announcement['summary'],
                style: TextStyle(
                  fontSize: 15,
                  color: Colors.blueGrey[700],
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
            SizedBox(height: 16),
            Row(
              children: [
                CircleAvatar(
                  radius: 16,
                  backgroundColor: Colors.blue.withOpacity(0.09),
                  child: Icon(Icons.person, size: 20, color: Colors.blue),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        announcement['author'] ?? widget.announcement.author,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (announcement['author_job'] != null)
                        Text(
                          announcement['author_job'],
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                    ],
                  ),
                ),
                Icon(Icons.schedule, size: 16, color: Colors.grey),
                SizedBox(width: 4),
                Text(
                  widget.announcement.createdDate != null
                      ? DateFormat('d MMM yyyy').format(widget.announcement.createdDate!)
                      : '',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContentCard(Map<String, dynamic> announcement) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.article, color: Colors.blue),
                SizedBox(width: 8),
                Text(
                  'Content',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            SizedBox(height: 16),
            Text(
              _removeHtmlTags(announcement['content'] ?? widget.announcement.content),
              style: TextStyle(
                fontSize: 15,
                height: 1.7,
                color: Colors.blueGrey[900],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAttachmentsCard(List<dynamic> attachments) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.attach_file, color: Colors.green),
                SizedBox(width: 8),
                Text(
                  'Attachments (${attachments.length})',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            SizedBox(height: 12),
            ...attachments.map((attachment) => _buildAttachmentItem(attachment)),
          ],
        ),
      ),
    );
  }

  Widget _buildAttachmentItem(dynamic attachment) {
    final att = attachment as Map<String, dynamic>;
    final name = att['name'] ?? 'Attachment';
    final size = att['size'] ?? 0;
    final type = att['type'] ?? '';

    IconData icon = Icons.insert_drive_file;
    Color color = Colors.grey;

    if (type.contains('image')) {
      icon = Icons.image;
      color = Colors.blue;
    } else if (type.contains('pdf')) {
      icon = Icons.picture_as_pdf;
      color = Colors.red;
    } else if (type.contains('word') || type.contains('document')) {
      icon = Icons.description;
      color = Colors.blue[700]!;
    } else if (type.contains('sheet') || type.contains('excel')) {
      icon = Icons.table_chart;
      color = Colors.green;
    }

    return ListTile(
      leading: Container(
        padding: EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.10),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: color, size: 24),
      ),
      title: Text(
        name,
        style: TextStyle(fontSize: 14),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        _formatFileSize(size),
        style: TextStyle(fontSize: 12, color: Colors.grey),
      ),
      trailing: Icon(Icons.download, color: Colors.grey),
      onTap: () => _openAttachment(att),
    );
  }

  Widget _buildAdditionalInfo(Map<String, dynamic> announcement) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.info_outline, color: Colors.orange),
                SizedBox(width: 8),
                Text(
                  'Additional Info',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            SizedBox(height: 12),
            if (announcement['start_date'] != null || announcement['end_date'] != null)
              _buildInfoRow(
                Icons.date_range,
                'Display Period',
                _formatDateRange(announcement['start_date'], announcement['end_date']),
              ),
            _buildInfoRow(
              Icons.visibility,
              'Read Count',
              '${announcement['read_count'] ?? 0} of ${announcement['target_count'] ?? 0}',
            ),
            if (announcement['read_percentage'] != null)
              _buildInfoRow(
                Icons.analytics,
                'Read Percentage',
                '${announcement['read_percentage'].toStringAsFixed(1)}%',
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey[600]),
          SizedBox(width: 8),
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String _formatDateRange(String? startDate, String? endDate) {
    if (startDate == null && endDate == null) return 'Not specified';

    final start = startDate != null ? DateTime.parse(startDate) : null;
    final end = endDate != null ? DateTime.parse(endDate) : null;

    if (start != null && end == null) {
      return 'From ${DateFormat('d MMM yyyy').format(start)}';
    }
    if (start == null && end != null) {
      return 'Until ${DateFormat('d MMM yyyy').format(end)}';
    }
    return '${DateFormat('d MMM').format(start!)} - ${DateFormat('d MMM yyyy').format(end!)}';
  }

  String _removeHtmlTags(String htmlText) {
    RegExp exp = RegExp(r"<[^>]*>", multiLine: true, caseSensitive: true);
    String plainText = htmlText.replaceAll(exp, '');

    plainText = plainText
        .replaceAll('&nbsp;', ' ')
        .replaceAll('&amp;', '&')
        .replaceAll('&lt;', '<')
        .replaceAll('&gt;', '>')
        .replaceAll('&quot;', '"')
        .replaceAll('&#39;', "'")
        .replaceAll('<br>', '\n')
        .replaceAll('<br/>', '\n')
        .replaceAll('<br />', '\n')
        .replaceAll('</p>', '\n\n')
        .replaceAll('</li>', '\n');

    return plainText.trim();
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
              'Failed to load details',
              style: TextStyle(fontSize: 16),
            ),
            SizedBox(height: 8),
            Text(
              errorMessage ?? '',
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadAnnouncementDetails,
              child: Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
