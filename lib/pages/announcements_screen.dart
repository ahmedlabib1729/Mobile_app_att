// lib/pages/announcements_screen.dart - Modern & English
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/employee.dart';
import '../models/announcement.dart';
import '../services/odoo_service.dart';
import 'announcement_details_screen.dart';

class AnnouncementsScreen extends StatefulWidget {
  final OdooService odooService;
  final Employee employee;

  const AnnouncementsScreen({
    Key? key,
    required this.odooService,
    required this.employee,
  }) : super(key: key);

  @override
  _AnnouncementsScreenState createState() => _AnnouncementsScreenState();
}

class _AnnouncementsScreenState extends State<AnnouncementsScreen> {
  List<Announcement> announcements = [];
  List<Announcement> filteredAnnouncements = [];
  List<Map<String, dynamic>> categories = [];

  bool isLoading = true;
  bool isLoadingMore = false;
  String? errorMessage;

  String selectedCategory = 'all';
  String searchQuery = '';
  final TextEditingController searchController = TextEditingController();

  int currentOffset = 0;
  final int pageSize = 20;
  bool hasMore = true;

  final ScrollController scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _loadInitialData();

    scrollController.addListener(() {
      if (scrollController.position.pixels >=
          scrollController.position.maxScrollExtent - 200) {
        _loadMoreAnnouncements();
      }
    });
  }

  @override
  void dispose() {
    searchController.dispose();
    scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadInitialData() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      final categoriesData = await widget.odooService.getAnnouncementCategories();
      final announcementsData = await widget.odooService.getAnnouncements(
        widget.employee.id,
        limit: pageSize,
        offset: 0,
      );

      setState(() {
        categories = categoriesData;
        announcements = announcementsData;
        filteredAnnouncements = announcementsData;
        currentOffset = announcementsData.length;
        hasMore = announcementsData.length == pageSize;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  Future<void> _loadMoreAnnouncements() async {
    if (isLoadingMore || !hasMore || searchQuery.isNotEmpty) return;

    try {
      setState(() {
        isLoadingMore = true;
      });

      final moreAnnouncements = await widget.odooService.getAnnouncements(
        widget.employee.id,
        limit: pageSize,
        offset: currentOffset,
      );

      setState(() {
        announcements.addAll(moreAnnouncements);
        _applyFilters();
        currentOffset += moreAnnouncements.length;
        hasMore = moreAnnouncements.length == pageSize;
        isLoadingMore = false;
      });
    } catch (e) {
      setState(() {
        isLoadingMore = false;
      });
    }
  }

  void _applyFilters() {
    setState(() {
      filteredAnnouncements = announcements.where((announcement) {
        bool matchesCategory = selectedCategory == 'all' ||
            announcement.type == selectedCategory;
        bool matchesSearch = searchQuery.isEmpty ||
            announcement.title.toLowerCase().contains(searchQuery.toLowerCase()) ||
            announcement.summary.toLowerCase().contains(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch;
      }).toList();
    });
  }

  Future<void> _performSearch(String query) async {
    if (query.isEmpty) {
      setState(() {
        searchQuery = '';
        _applyFilters();
      });
      return;
    }

    try {
      setState(() {
        isLoading = true;
        searchQuery = query;
      });

      final searchResults = await widget.odooService.searchAnnouncements(
        widget.employee.id,
        query,
        category: selectedCategory,
      );

      setState(() {
        filteredAnnouncements = searchResults;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        isLoading = false;
      });
    }
  }

  void _viewAnnouncementDetails(Announcement announcement) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AnnouncementDetailsScreen(
          announcement: announcement,
          odooService: widget.odooService,
          employee: widget.employee,
        ),
      ),
    ).then((_) {
      _loadInitialData();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFFF6F8FC),
      appBar: AppBar(
        title: Text('Announcements', style: TextStyle(color: Colors.black)),
        backgroundColor: Colors.white,
        elevation: 1,
        iconTheme: IconThemeData(color: Colors.black),
        actions: [
          // Unread count
          if (announcements.where((a) => !a.isRead).isNotEmpty)
            Container(
              padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              margin: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${announcements.where((a) => !a.isRead).length} New',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadInitialData,
          ),
        ],
      ),
      body: isLoading && announcements.isEmpty
          ? Center(child: CircularProgressIndicator())
          : errorMessage != null && announcements.isEmpty
          ? _buildErrorWidget()
          : Column(
        children: [
          _buildSearchBar(),
          _buildCategoryFilters(),
          Expanded(child: _buildAnnouncementsList()),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      padding: EdgeInsets.all(16),
      color: Colors.white,
      child: TextField(
        controller: searchController,
        decoration: InputDecoration(
          hintText: 'Search announcements...',
          prefixIcon: Icon(Icons.search),
          suffixIcon: searchController.text.isNotEmpty
              ? IconButton(
            icon: Icon(Icons.clear),
            onPressed: () {
              searchController.clear();
              _performSearch('');
            },
          )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: BorderSide.none,
          ),
          filled: true,
          fillColor: Colors.grey[100],
          contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 0),
        ),
        onChanged: (value) {
          if (value.isEmpty || value.length >= 3) {
            _performSearch(value);
          }
        },
      ),
    );
  }

  Widget _buildCategoryFilters() {
    return Container(
      height: 50,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.symmetric(horizontal: 16),
        itemCount: categories.length,
        itemBuilder: (context, index) {
          final category = categories[index];
          final isSelected = selectedCategory == category['id'];

          return Padding(
            padding: EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(category['icon'] ?? '', style: TextStyle(fontSize: 16)),
                  SizedBox(width: 4),
                  Text(category['name'] ?? ''),
                ],
              ),
              selected: isSelected,
              selectedColor: Color(int.parse(
                  '0xFF${(category['color'] ?? '#2196F3').substring(1)}'))
                  .withOpacity(0.16),
              backgroundColor: Colors.grey[100],
              onSelected: (selected) {
                setState(() {
                  selectedCategory = selected ? category['id'] : 'all';
                  _applyFilters();
                });
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildAnnouncementsList() {
    if (filteredAnnouncements.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.campaign_outlined, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No announcements found',
              style: TextStyle(fontSize: 18, color: Colors.grey[600]),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadInitialData,
      child: ListView.builder(
        controller: scrollController,
        padding: EdgeInsets.all(16),
        itemCount: filteredAnnouncements.length + (isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == filteredAnnouncements.length) {
            return Center(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: CircularProgressIndicator(),
              ),
            );
          }

          final announcement = filteredAnnouncements[index];
          return _buildAnnouncementCard(announcement);
        },
      ),
    );
  }

  Widget _buildAnnouncementCard(Announcement announcement) {
    return Card(
      margin: EdgeInsets.only(bottom: 12),
      elevation: announcement.isPinned ? 5 : 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: announcement.isPinned
            ? BorderSide(color: Colors.red.withOpacity(0.25), width: 2)
            : BorderSide.none,
      ),
      child: InkWell(
        onTap: () => _viewAnnouncementDetails(announcement),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  if (announcement.isPinned)
                    Container(
                      padding: EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: Colors.red.withOpacity(0.10),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.push_pin,
                        size: 16,
                        color: Colors.red,
                      ),
                    ),
                  if (announcement.isPinned) SizedBox(width: 8),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Color(int.parse(
                          '0xFF${announcement.typeColor.substring(1)}'))
                          .withOpacity(0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(announcement.typeIcon, style: TextStyle(fontSize: 14)),
                        SizedBox(width: 4),
                        Text(
                          announcement.typeText,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: Color(
                                int.parse('0xFF${announcement.typeColor.substring(1)}')),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Spacer(),
                  if (!announcement.isRead)
                    Container(
                      padding: EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: Colors.blue,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.fiber_new,
                        size: 16,
                        color: Colors.white,
                      ),
                    ),
                  if (announcement.priority == 'high' ||
                      announcement.priority == 'urgent')
                    Padding(
                      padding: EdgeInsets.only(left: 8),
                      child: Text(
                        announcement.priorityIcon,
                        style: TextStyle(
                          fontSize: 20,
                          color: Color(int.parse(
                              '0xFF${announcement.priorityColor.substring(1)}')),
                        ),
                      ),
                    ),
                ],
              ),
              SizedBox(height: 12),
              Text(
                announcement.title,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: announcement.isRead ? Colors.black87 : Colors.black,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (announcement.summary.isNotEmpty) ...[
                SizedBox(height: 8),
                Text(
                  announcement.summary,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey[600],
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              SizedBox(height: 12),
              Row(
                children: [
                  Icon(Icons.schedule, size: 14, color: Colors.grey),
                  SizedBox(width: 4),
                  Text(
                    announcement.createdDate != null
                        ? DateFormat('d MMM yyyy').format(announcement.createdDate!)
                        : '',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  SizedBox(width: 16),
                  Icon(Icons.person_outline, size: 14, color: Colors.grey),
                  SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      announcement.author,
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (announcement.attachments.isNotEmpty) ...[
                    SizedBox(width: 8),
                    Icon(Icons.attach_file, size: 16, color: Colors.grey),
                    SizedBox(width: 2),
                    Text(
                      '${announcement.attachments.length}',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
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
              'Failed to load announcements',
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
              onPressed: _loadInitialData,
              child: Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
