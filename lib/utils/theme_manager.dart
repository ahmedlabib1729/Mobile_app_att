// theme_manager.dart - إدارة المظاهر والألوان
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeManager extends ChangeNotifier {
  static final ThemeManager _instance = ThemeManager._internal();
  factory ThemeManager() => _instance;
  ThemeManager._internal();

  // مفاتيح التخزين
  static const String _themeKey = 'app_theme_mode';
  static const String _primaryColorKey = 'app_primary_color';
  static const String _fontSizeKey = 'app_font_size';

  // الألوان الأساسية للتطبيق
  static const Color primaryColor = Color(0xFF1976D2);
  static const Color secondaryColor = Color(0xFF0D47A1);
  static const Color accentColor = Color(0xFF03DAC6);
  static const Color successColor = Color(0xFF4CAF50);
  static const Color warningColor = Color(0xFFFF9800);
  static const Color errorColor = Color(0xFFF44336);
  static const Color infoColor = Color(0xFF2196F3);

  // ألوان إضافية
  static const Color lightGrey = Color(0xFFF5F5F5);
  static const Color mediumGrey = Color(0xFF9E9E9E);
  static const Color darkGrey = Color(0xFF424242);

  // متغيرات المظهر
  bool _isDarkMode = false;
  Color _currentPrimaryColor = primaryColor;
  double _fontSizeMultiplier = 1.0;

  // Getters
  bool get isDarkMode => _isDarkMode;
  Color get currentPrimaryColor => _currentPrimaryColor;
  double get fontSizeMultiplier => _fontSizeMultiplier;

  // ألوان المظهر الحالي
  static const Map<String, Color> lightColors = {
    'primary': primaryColor,
    'secondary': secondaryColor,
    'accent': accentColor,
    'success': successColor,
    'warning': warningColor,
    'error': errorColor,
    'info': infoColor,
    'background': Colors.white,
    'surface': Colors.white,
    'onPrimary': Colors.white,
    'onSecondary': Colors.white,
    'onBackground': Colors.black87,
    'onSurface': Colors.black87,
  };

  static const Map<String, Color> darkColors = {
    'primary': Color(0xFF90CAF9),
    'secondary': Color(0xFF1565C0),
    'accent': accentColor,
    'success': Color(0xFF66BB6A),
    'warning': Color(0xFFFFB74D),
    'error': Color(0xFFEF5350),
    'info': Color(0xFF42A5F5),
    'background': Color(0xFF121212),
    'surface': Color(0xFF1E1E1E),
    'onPrimary': Colors.black,
    'onSecondary': Colors.white,
    'onBackground': Colors.white,
    'onSurface': Colors.white,
  };

  // تهيئة المظهر من التخزين المحلي
  Future<void> initializeTheme() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      _isDarkMode = prefs.getBool(_themeKey) ?? false;

      final primaryColorValue = prefs.getInt(_primaryColorKey);
      if (primaryColorValue != null) {
        _currentPrimaryColor = Color(primaryColorValue);
      }

      _fontSizeMultiplier = prefs.getDouble(_fontSizeKey) ?? 1.0;

      notifyListeners();
      print('تم تحميل إعدادات المظهر: Dark=$_isDarkMode, Primary=${_currentPrimaryColor.value}');
    } catch (e) {
      print('خطأ في تحميل إعدادات المظهر: $e');
    }
  }

  // تبديل المظهر الفاتح/الداكن
  Future<void> toggleTheme() async {
    _isDarkMode = !_isDarkMode;
    await _saveThemeSettings();
    notifyListeners();
  }

  // تعيين مظهر محدد
  Future<void> setThemeMode(bool isDark) async {
    if (_isDarkMode != isDark) {
      _isDarkMode = isDark;
      await _saveThemeSettings();
      notifyListeners();
    }
  }

  // تغيير اللون الأساسي
  Future<void> setPrimaryColor(Color color) async {
    if (_currentPrimaryColor != color) {
      _currentPrimaryColor = color;
      await _saveThemeSettings();
      notifyListeners();
    }
  }

  // تغيير حجم الخط
  Future<void> setFontSizeMultiplier(double multiplier) async {
    if (_fontSizeMultiplier != multiplier) {
      _fontSizeMultiplier = multiplier;
      await _saveThemeSettings();
      notifyListeners();
    }
  }

  // حفظ إعدادات المظهر
  Future<void> _saveThemeSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_themeKey, _isDarkMode);
      await prefs.setInt(_primaryColorKey, _currentPrimaryColor.value);
      await prefs.setDouble(_fontSizeKey, _fontSizeMultiplier);
    } catch (e) {
      print('خطأ في حفظ إعدادات المظهر: $e');
    }
  }

  // إنشاء المظهر الفاتح
  ThemeData get lightTheme => ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    primarySwatch: _createMaterialColor(_currentPrimaryColor),
    primaryColor: _currentPrimaryColor,
    colorScheme: ColorScheme.fromSeed(
      seedColor: _currentPrimaryColor,
      brightness: Brightness.light,
    ),

    // شريط التطبيق
    appBarTheme: AppBarTheme(
      backgroundColor: _currentPrimaryColor,
      foregroundColor: Colors.white,
      elevation: 2,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontSize: 18 * _fontSizeMultiplier,
        fontWeight: FontWeight.bold,
        color: Colors.white,
      ),
      iconTheme: IconThemeData(color: Colors.white),
    ),

    // الأزرار المرفوعة
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: _currentPrimaryColor,
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        elevation: 3,
        textStyle: TextStyle(
          fontSize: 16 * _fontSizeMultiplier,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),

    // الأزرار النصية
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: _currentPrimaryColor,
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        textStyle: TextStyle(
          fontSize: 14 * _fontSizeMultiplier,
          fontWeight: FontWeight.w500,
        ),
      ),
    ),

    // البطاقات
    cardTheme: CardTheme(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      margin: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      color: Colors.white,
      shadowColor: Colors.black26,
    ),

    // حقول الإدخال
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.grey.shade300),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: _currentPrimaryColor, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: errorColor, width: 2),
      ),
      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      labelStyle: TextStyle(
        fontSize: 16 * _fontSizeMultiplier,
        color: Colors.grey.shade600,
      ),
      hintStyle: TextStyle(
        fontSize: 14 * _fontSizeMultiplier,
        color: Colors.grey.shade400,
      ),
    ),

    // شريط الإشعارات
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      contentTextStyle: TextStyle(
        fontSize: 14 * _fontSizeMultiplier,
        color: Colors.white,
      ),
    ),

    // النصوص
    textTheme: _createTextTheme(Brightness.light),

    // الألوان العامة
    scaffoldBackgroundColor: lightGrey,
    dividerColor: Colors.grey.shade300,
    disabledColor: Colors.grey.shade400,
  );

  // إنشاء المظهر الداكن
  ThemeData get darkTheme => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    primarySwatch: _createMaterialColor(_currentPrimaryColor),
    primaryColor: _currentPrimaryColor,
    colorScheme: ColorScheme.fromSeed(
      seedColor: _currentPrimaryColor,
      brightness: Brightness.dark,
    ),

    // شريط التطبيق
    appBarTheme: AppBarTheme(
      backgroundColor: Color(0xFF1F1F1F),
      foregroundColor: Colors.white,
      elevation: 2,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontSize: 18 * _fontSizeMultiplier,
        fontWeight: FontWeight.bold,
        color: Colors.white,
      ),
      iconTheme: IconThemeData(color: Colors.white),
    ),

    // الأزرار المرفوعة
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: _currentPrimaryColor,
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        elevation: 3,
        textStyle: TextStyle(
          fontSize: 16 * _fontSizeMultiplier,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),

    // البطاقات
    cardTheme: CardTheme(
      color: Color(0xFF2C2C2C),
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      margin: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      shadowColor: Colors.black45,
    ),

    // حقول الإدخال
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.grey.shade600),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.grey.shade600),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: _currentPrimaryColor, width: 2),
      ),
      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      labelStyle: TextStyle(
        fontSize: 16 * _fontSizeMultiplier,
        color: Colors.grey.shade400,
      ),
      hintStyle: TextStyle(
        fontSize: 14 * _fontSizeMultiplier,
        color: Colors.grey.shade500,
      ),
    ),

    // النصوص
    textTheme: _createTextTheme(Brightness.dark),

    // الألوان العامة
    scaffoldBackgroundColor: Color(0xFF121212),
    dividerColor: Colors.grey.shade700,
    disabledColor: Colors.grey.shade600,
  );

  // إنشاء نسق النصوص
  TextTheme _createTextTheme(Brightness brightness) {
    final Color textColor = brightness == Brightness.light
        ? Colors.black87
        : Colors.white;
    final Color secondaryTextColor = brightness == Brightness.light
        ? Colors.black54
        : Colors.white70;

    return TextTheme(
      displayLarge: TextStyle(
        fontSize: 32 * _fontSizeMultiplier,
        fontWeight: FontWeight.bold,
        color: textColor,
      ),
      displayMedium: TextStyle(
        fontSize: 28 * _fontSizeMultiplier,
        fontWeight: FontWeight.bold,
        color: textColor,
      ),
      displaySmall: TextStyle(
        fontSize: 24 * _fontSizeMultiplier,
        fontWeight: FontWeight.bold,
        color: textColor,
      ),
      headlineLarge: TextStyle(
        fontSize: 22 * _fontSizeMultiplier,
        fontWeight: FontWeight.w600,
        color: textColor,
      ),
      headlineMedium: TextStyle(
        fontSize: 20 * _fontSizeMultiplier,
        fontWeight: FontWeight.w600,
        color: textColor,
      ),
      headlineSmall: TextStyle(
        fontSize: 18 * _fontSizeMultiplier,
        fontWeight: FontWeight.w600,
        color: textColor,
      ),
      titleLarge: TextStyle(
        fontSize: 16 * _fontSizeMultiplier,
        fontWeight: FontWeight.w600,
        color: textColor,
      ),
      titleMedium: TextStyle(
        fontSize: 14 * _fontSizeMultiplier,
        fontWeight: FontWeight.w500,
        color: textColor,
      ),
      titleSmall: TextStyle(
        fontSize: 12 * _fontSizeMultiplier,
        fontWeight: FontWeight.w500,
        color: textColor,
      ),
      bodyLarge: TextStyle(
        fontSize: 16 * _fontSizeMultiplier,
        fontWeight: FontWeight.normal,
        color: textColor,
      ),
      bodyMedium: TextStyle(
        fontSize: 14 * _fontSizeMultiplier,
        fontWeight: FontWeight.normal,
        color: textColor,
      ),
      bodySmall: TextStyle(
        fontSize: 12 * _fontSizeMultiplier,
        fontWeight: FontWeight.normal,
        color: secondaryTextColor,
      ),
      labelLarge: TextStyle(
        fontSize: 14 * _fontSizeMultiplier,
        fontWeight: FontWeight.w500,
        color: textColor,
      ),
      labelMedium: TextStyle(
        fontSize: 12 * _fontSizeMultiplier,
        fontWeight: FontWeight.w500,
        color: textColor,
      ),
      labelSmall: TextStyle(
        fontSize: 10 * _fontSizeMultiplier,
        fontWeight: FontWeight.w500,
        color: secondaryTextColor,
      ),
    );
  }

  // إنشاء MaterialColor من Color
  MaterialColor _createMaterialColor(Color color) {
    List strengths = <double>[.05];
    Map<int, Color> swatch = <int, Color>{};
    final int r = color.red, g = color.green, b = color.blue;

    for (int i = 1; i < 10; i++) {
      strengths.add(0.1 * i);
    }

    for (var strength in strengths) {
      final double ds = 0.5 - strength;
      swatch[(strength * 1000).round()] = Color.fromRGBO(
        r + ((ds < 0 ? r : (255 - r)) * ds).round(),
        g + ((ds < 0 ? g : (255 - g)) * ds).round(),
        b + ((ds < 0 ? b : (255 - b)) * ds).round(),
        1,
      );
    }

    return MaterialColor(color.value, swatch);
  }

  // الحصول على لون من المجموعة الحالية
  Color getColor(String colorName) {
    final colors = _isDarkMode ? darkColors : lightColors;
    return colors[colorName] ?? _currentPrimaryColor;
  }

  // ألوان محددة مسبقاً للاختيار
  static const List<Color> predefinedColors = [
    Color(0xFF1976D2), // الأزرق الافتراضي
    Color(0xFF388E3C), // الأخضر
    Color(0xFFF57C00), // البرتقالي
    Color(0xFFD32F2F), // الأحمر
    Color(0xFF7B1FA2), // البنفسجي
    Color(0xFF0097A7), // الأزرق المخضر
    Color(0xFF5D4037), // البني
    Color(0xFF455A64), // الرمادي الأزرق
  ];

  // إعادة تعيين المظهر للافتراضي
  Future<void> resetToDefaults() async {
    _isDarkMode = false;
    _currentPrimaryColor = primaryColor;
    _fontSizeMultiplier = 1.0;
    await _saveThemeSettings();
    notifyListeners();
  }

  // الحصول على تباين لون النص
  Color getTextColorForBackground(Color backgroundColor) {
    // حساب luminance للون الخلفية
    final luminance = backgroundColor.computeLuminance();

    // إذا كان اللون فاتح، استخدم نص داكن، والعكس
    return luminance > 0.5 ? Colors.black87 : Colors.white;
  }

  // الحصول على لون مخفف
  Color getLighterColor(Color color, [double amount = 0.1]) {
    final hsl = HSLColor.fromColor(color);
    final lightness = (hsl.lightness + amount).clamp(0.0, 1.0);
    return hsl.withLightness(lightness).toColor();
  }

  // الحصول على لون داكن
  Color getDarkerColor(Color color, [double amount = 0.1]) {
    final hsl = HSLColor.fromColor(color);
    final lightness = (hsl.lightness - amount).clamp(0.0, 1.0);
    return hsl.withLightness(lightness).toColor();
  }
}