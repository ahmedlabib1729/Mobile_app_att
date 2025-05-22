// lib/widgets/employee_avatar.dart - ويدجت بسيط بدون مكتبات خارجية
import 'package:flutter/material.dart';
import '../models/employee.dart';
import '../services/odoo_service.dart';

class EmployeeAvatar extends StatelessWidget {
  final Employee employee;
  final double radius;
  final bool showEditButton;
  final VoidCallback? onEdit;
  final OdooService? odooService;

  const EmployeeAvatar({
    Key? key,
    required this.employee,
    this.radius = 40,
    this.showEditButton = false,
    this.onEdit,
    this.odooService,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // الصورة الرئيسية
        CircleAvatar(
          radius: radius,
          backgroundColor: Colors.grey[300],
          backgroundImage: employee.hasImage
              ? NetworkImage(employee.bestAvailableImage!)
              : null,
          child: !employee.hasImage
              ? Icon(
            Icons.person,
            size: radius * 0.8,
            color: Colors.white,
          )
              : null,
          onBackgroundImageError: (exception, stackTrace) {
            // في حالة فشل تحميل الصورة، سيتم عرض الأيقونة الافتراضية
            print('فشل في تحميل صورة الموظف: $exception');
          },
        ),

        // زر التعديل (اختياري)
        if (showEditButton && onEdit != null)
          Positioned(
            bottom: 0,
            right: 0,
            child: GestureDetector(
              onTap: onEdit,
              child: Container(
                width: radius * 0.6,
                height: radius * 0.6,
                decoration: BoxDecoration(
                  color: Colors.blue,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: Icon(
                  Icons.camera_alt,
                  color: Colors.white,
                  size: radius * 0.3,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

// ويدجت متقدم للصورة مع ميزات إضافية
class AdvancedEmployeeAvatar extends StatefulWidget {
  final Employee employee;
  final double radius;
  final bool showBadge;
  final bool showEditButton;
  final bool showBorder;
  final Color? borderColor;
  final VoidCallback? onTap;
  final VoidCallback? onEdit;
  final OdooService? odooService;
  final String? statusText;
  final Color? statusColor;

  const AdvancedEmployeeAvatar({
    Key? key,
    required this.employee,
    this.radius = 40,
    this.showBadge = false,
    this.showEditButton = false,
    this.showBorder = true,
    this.borderColor,
    this.onTap,
    this.onEdit,
    this.odooService,
    this.statusText,
    this.statusColor,
  }) : super(key: key);

  @override
  _AdvancedEmployeeAvatarState createState() => _AdvancedEmployeeAvatarState();
}

class _AdvancedEmployeeAvatarState extends State<AdvancedEmployeeAvatar>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    setState(() => _isPressed = true);
    _animationController.forward();
  }

  void _handleTapUp(TapUpDetails details) {
    setState(() => _isPressed = false);
    _animationController.reverse();
    if (widget.onTap != null) widget.onTap!();
  }

  void _handleTapCancel() {
    setState(() => _isPressed = false);
    _animationController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _scaleAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: GestureDetector(
            onTapDown: widget.onTap != null ? _handleTapDown : null,
            onTapUp: widget.onTap != null ? _handleTapUp : null,
            onTapCancel: widget.onTap != null ? _handleTapCancel : null,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                // الصورة مع الحدود
                Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: widget.showBorder
                        ? Border.all(
                      color: widget.borderColor ?? Colors.blue,
                      width: 3,
                    )
                        : null,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.1),
                        blurRadius: 8,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: EmployeeAvatar(
                    employee: widget.employee,
                    radius: widget.radius,
                    odooService: widget.odooService,
                  ),
                ),

                // شارة الحالة
                if (widget.showBadge)
                  Positioned(
                    top: -2,
                    right: -2,
                    child: Container(
                      width: widget.radius * 0.4,
                      height: widget.radius * 0.4,
                      decoration: BoxDecoration(
                        color: widget.statusColor ?? Colors.green,
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2),
                      ),
                    ),
                  ),

                // زر التعديل
                if (widget.showEditButton && widget.onEdit != null)
                  Positioned(
                    bottom: -2,
                    right: -2,
                    child: GestureDetector(
                      onTap: widget.onEdit,
                      child: Container(
                        width: widget.radius * 0.5,
                        height: widget.radius * 0.5,
                        decoration: BoxDecoration(
                          color: Colors.blue,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.2),
                              blurRadius: 4,
                              offset: Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Icon(
                          Icons.camera_alt,
                          color: Colors.white,
                          size: widget.radius * 0.25,
                        ),
                      ),
                    ),
                  ),

                // نص الحالة
                if (widget.statusText != null)
                  Positioned(
                    bottom: -widget.radius * 0.3,
                    left: -widget.radius * 0.2,
                    right: -widget.radius * 0.2,
                    child: Container(
                      padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: widget.statusColor ?? Colors.green,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        widget.statusText!,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: widget.radius * 0.2,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

// ويدجت قائمة صور الموظفين
class EmployeeAvatarList extends StatelessWidget {
  final List<Employee> employees;
  final double avatarRadius;
  final int maxVisible;
  final VoidCallback? onMoreTap;
  final Function(Employee)? onEmployeeTap;
  final OdooService? odooService;

  const EmployeeAvatarList({
    Key? key,
    required this.employees,
    this.avatarRadius = 25,
    this.maxVisible = 5,
    this.onMoreTap,
    this.onEmployeeTap,
    this.odooService,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final visibleEmployees = employees.take(maxVisible).toList();
    final remainingCount = employees.length - maxVisible;

    return Row(
      children: [
        // الموظفين المرئيين
        ...visibleEmployees.asMap().entries.map((entry) {
          final index = entry.key;
          final employee = entry.value;

          return Transform.translate(
            offset: Offset(-index * avatarRadius * 0.7, 0),
            child: GestureDetector(
              onTap: () => onEmployeeTap?.call(employee),
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: EmployeeAvatar(
                  employee: employee,
                  radius: avatarRadius,
                  odooService: odooService,
                ),
              ),
            ),
          );
        }).toList(),

        // زر "المزيد"
        if (remainingCount > 0)
          Transform.translate(
            offset: Offset(-maxVisible * avatarRadius * 0.7, 0),
            child: GestureDetector(
              onTap: onMoreTap,
              child: Container(
                width: avatarRadius * 2,
                height: avatarRadius * 2,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: Center(
                  child: Text(
                    '+$remainingCount',
                    style: TextStyle(
                      fontSize: avatarRadius * 0.4,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey[600],
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}