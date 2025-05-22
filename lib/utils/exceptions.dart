abstract class AppException implements Exception {
  final String message;
  final String? details;
  final int? statusCode;

  AppException(this.message, {this.details, this.statusCode});

  @override
  String toString() => message;
}

class NetworkException extends AppException {
  NetworkException([String message = 'مشكلة في الاتصال بالشبكة'])
      : super(message);
}

class ServerException extends AppException {
  ServerException([String message = 'خطأ في الخادم', int? statusCode])
      : super(message, statusCode: statusCode);
}

class AuthenticationException extends AppException {
  AuthenticationException([String message = 'خطأ في المصادقة'])
      : super(message);
}

class ValidationException extends AppException {
  ValidationException([String message = 'بيانات غير صالحة'])
      : super(message);
}

class PermissionException extends AppException {
  PermissionException([String message = 'ليس لديك صلاحية للقيام بهذا الإجراء'])
      : super(message);
}

class DataNotFoundException extends AppException {
  DataNotFoundException([String message = 'البيانات المطلوبة غير موجودة'])
      : super(message);
}