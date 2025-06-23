// lib/widgets/language_switcher.dart
import 'package:flutter/material.dart';
import '../services/language_manager.dart';

class LanguageSwitcher extends StatelessWidget {
  final bool showText;
  final Color? iconColor;
  final Color? backgroundColor;
  final double? iconSize;

  const LanguageSwitcher({
    Key? key,
    this.showText = false,
    this.iconColor,
    this.backgroundColor,
    this.iconSize,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final langManager = LanguageManager();

    return AnimatedBuilder(
      animation: langManager,
      builder: (context, child) {
        final isArabic = langManager.isArabic;

        if (showText) {
          // عرض كزر مع نص
          return Container(
            decoration: BoxDecoration(
              color: backgroundColor ?? Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _showLanguageDialog(context),
                borderRadius: BorderRadius.circular(20),
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.language,
                        color: iconColor ?? Colors.white,
                        size: iconSize ?? 20,
                      ),
                      SizedBox(width: 6),
                      Text(
                        isArabic ? 'العربية' : 'English',
                        style: TextStyle(
                          color: iconColor ?? Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      SizedBox(width: 4),
                      Icon(
                        Icons.arrow_drop_down,
                        color: iconColor ?? Colors.white,
                        size: 18,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        } else {
          // عرض كأيقونة فقط
          return Container(
            decoration: BoxDecoration(
              color: backgroundColor ?? Colors.white.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: IconButton(
              icon: Icon(
                Icons.language,
                color: iconColor ?? Colors.white,
                size: iconSize ?? 24,
              ),
              onPressed: () => _showLanguageDialog(context),
              tooltip: langManager.translate('language'),
            ),
          );
        }
      },
    );
  }

  void _showLanguageDialog(BuildContext context) {
    final langManager = LanguageManager();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        title: Row(
          children: [
            Icon(Icons.language, color: Color(0xFF2196F3)),
            SizedBox(width: 12),
            Text(langManager.translate('language')),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildLanguageOption(
              context,
              'English',
              'en',
              Icons.abc,
              !langManager.isArabic,
            ),
            SizedBox(height: 8),
            _buildLanguageOption(
              context,
              'العربية',
              'ar',
              Icons.text_fields,
              langManager.isArabic,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLanguageOption(
      BuildContext context,
      String title,
      String languageCode,
      IconData icon,
      bool isSelected,
      ) {
    return Container(
      decoration: BoxDecoration(
        color: isSelected ? Color(0xFF2196F3).withOpacity(0.1) : Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isSelected ? Color(0xFF2196F3) : Colors.grey.withOpacity(0.3),
          width: isSelected ? 2 : 1,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () async {
            final langManager = LanguageManager();
            await langManager.changeLanguage(languageCode);

            // إعادة بناء التطبيق بالكامل
            Navigator.of(context).pop();

            // إظهار رسالة نجاح
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                  languageCode == 'ar'
                      ? 'تم تغيير اللغة إلى العربية'
                      : 'Language changed to English',
                ),
                backgroundColor: Colors.green,
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            );
          },
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  icon,
                  color: isSelected ? Color(0xFF2196F3) : Colors.grey[600],
                ),
                SizedBox(width: 12),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? Color(0xFF2196F3) : Colors.grey[800],
                  ),
                ),
                Spacer(),
                if (isSelected)
                  Icon(
                    Icons.check_circle,
                    color: Color(0xFF2196F3),
                    size: 20,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// زر سريع لتغيير اللغة (يغير مباشرة بدون dialog)
class QuickLanguageSwitcher extends StatelessWidget {
  final Color? color;

  const QuickLanguageSwitcher({Key? key, this.color}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final langManager = LanguageManager();

    return AnimatedBuilder(
      animation: langManager,
      builder: (context, child) {
        return GestureDetector(
          onTap: () async {
            final newLang = langManager.isArabic ? 'en' : 'ar';
            await langManager.changeLanguage(newLang);
          },
          child: Container(
            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              border: Border.all(
                color: color ?? Theme.of(context).primaryColor,
                width: 1.5,
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              langManager.isArabic ? 'EN' : 'ع',
              style: TextStyle(
                color: color ?? Theme.of(context).primaryColor,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ),
        );
      },
    );
  }
}