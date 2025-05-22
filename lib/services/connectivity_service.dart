// services/connectivity_service.dart - نسخة مبسطة
import 'dart:async';
import 'dart:io';

class ConnectivityService {
  static final ConnectivityService _instance = ConnectivityService._internal();
  factory ConnectivityService() => _instance;
  ConnectivityService._internal();

  bool _isOnline = true;
  bool get isOnline => _isOnline;

  final StreamController<bool> _connectionStatusController =
  StreamController<bool>.broadcast();
  Stream<bool> get connectionStatusStream => _connectionStatusController.stream;

  Timer? _periodicCheckTimer;

  // بدء مراقبة الاتصال
  void startMonitoring() {
    print('بدء مراقبة حالة الاتصال...');

    // فحص الحالة الحالية
    _checkCurrentConnection();

    // بدء الفحص الدوري (كل 30 ثانية)
    _startPeriodicCheck();
  }

  // التحقق من الحالة الحالية للاتصال
  Future<void> _checkCurrentConnection() async {
    try {
      final hasInternet = await _hasInternetConnection();
      _setConnectionStatus(hasInternet);
    } catch (e) {
      print('خطأ في فحص الحالة الحالية للاتصال: $e');
      _setConnectionStatus(false);
    }
  }

  // تعيين حالة الاتصال وإشعار المستمعين
  void _setConnectionStatus(bool isOnline) {
    if (_isOnline != isOnline) {
      _isOnline = isOnline;
      _connectionStatusController.add(_isOnline);
      print('حالة الاتصال تغيرت إلى: ${_isOnline ? "متصل" : "غير متصل"}');
    }
  }

  // فحص الاتصال الفعلي بالإنترنت
  Future<bool> _hasInternetConnection() async {
    try {
      // محاولة الاتصال بـ Google DNS
      final result = await InternetAddress.lookup('google.com')
          .timeout(Duration(seconds: 5));

      if (result.isNotEmpty && result[0].rawAddress.isNotEmpty) {
        return true;
      }

      return false;
    } catch (e) {
      print('خطأ في فحص الاتصال بالإنترنت: $e');
      return false;
    }
  }

  // فحص اتصال مخصص بخادم معين
  Future<bool> checkServerConnection(String serverUrl) async {
    try {
      final uri = Uri.parse(serverUrl);
      final result = await InternetAddress.lookup(uri.host)
          .timeout(Duration(seconds: 10));

      return result.isNotEmpty;
    } catch (e) {
      print('خطأ في فحص الاتصال بالخادم $serverUrl: $e');
      return false;
    }
  }

  // بدء الفحص الدوري
  void _startPeriodicCheck() {
    _periodicCheckTimer?.cancel();

    _periodicCheckTimer = Timer.periodic(
      Duration(seconds: 30),
          (timer) async {
        final hasInternet = await _hasInternetConnection();
        _setConnectionStatus(hasInternet);
      },
    );
  }

  // الحصول على معلومات مفصلة عن الاتصال
  Future<Map<String, dynamic>> getConnectionInfo() async {
    try {
      final hasInternet = await _hasInternetConnection();

      return {
        'is_connected': hasInternet,
        'connection_type': hasInternet ? 'متصل' : 'غير متصل',
        'connection_speed': hasInternet ? 'عادي' : 'لا يوجد',
        'timestamp': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      print('خطأ في الحصول على معلومات الاتصال: $e');
      return {
        'is_connected': false,
        'connection_type': 'خطأ',
        'connection_speed': 'غير متاح',
        'timestamp': DateTime.now().toIso8601String(),
        'error': e.toString(),
      };
    }
  }

  // انتظار الاتصال (مفيد للعمليات الحساسة)
  Future<bool> waitForConnection({Duration timeout = const Duration(seconds: 30)}) async {
    if (_isOnline) return true;

    final completer = Completer<bool>();
    StreamSubscription? subscription;
    Timer? timeoutTimer;

    // الاستماع لتغيير حالة الاتصال
    subscription = connectionStatusStream.listen((isOnline) {
      if (isOnline && !completer.isCompleted) {
        subscription?.cancel();
        timeoutTimer?.cancel();
        completer.complete(true);
      }
    });

    // مؤقت انتهاء الوقت
    timeoutTimer = Timer(timeout, () {
      if (!completer.isCompleted) {
        subscription?.cancel();
        completer.complete(false);
      }
    });

    return completer.future;
  }

  // إعادة تعيين حالة الاتصال
  Future<void> resetConnectionStatus() async {
    print('إعادة تعيين حالة الاتصال...');
    await _checkCurrentConnection();
  }

  // تعطيل الفحص الدوري
  void pauseMonitoring() {
    print('تم إيقاف مراقبة الاتصال مؤقتاً');
    _periodicCheckTimer?.cancel();
  }

  // استئناف الفحص الدوري
  void resumeMonitoring() {
    print('تم استئناف مراقبة الاتصال');
    _startPeriodicCheck();
    _checkCurrentConnection();
  }

  // الحصول على إحصائيات الاتصال
  Map<String, dynamic> getConnectionStats() {
    return {
      'current_status': _isOnline ? 'متصل' : 'غير متصل',
      'periodic_check_active': _periodicCheckTimer?.isActive ?? false,
      'listeners_count': _connectionStatusController.hasListener ? 'نعم' : 'لا',
    };
  }

  // إيقاف المراقبة
  void dispose() {
    print('إيقاف خدمة مراقبة الاتصال...');

    _periodicCheckTimer?.cancel();
    _periodicCheckTimer = null;

    _connectionStatusController.close();

    print('تم إيقاف خدمة مراقبة الاتصال');
  }

  // إعدادات متقدمة للخدمة
  void configure({
    Duration? periodicCheckInterval,
  }) {
    if (periodicCheckInterval != null) {
      _periodicCheckTimer?.cancel();
      _periodicCheckTimer = Timer.periodic(
        periodicCheckInterval,
            (timer) async {
          final hasInternet = await _hasInternetConnection();
          _setConnectionStatus(hasInternet);
        },
      );
      print('تم تحديث فترة الفحص الدوري إلى: ${periodicCheckInterval.inSeconds} ثانية');
    }
  }
}