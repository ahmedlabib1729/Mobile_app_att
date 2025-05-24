import 'package:flutter/material.dart';
import 'home_page.dart';
import '../services/odoo_service.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({Key? key}) : super(key: key);

  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _rememberMe = false;
  bool _obscurePassword = true;
  bool _isLoading = false;

  // Odoo Service
  final OdooService _odooService = OdooService(
    url: 'http://192.168.64.132:8018/',
    database: 'hr_emp',
  );

  @override
  void initState() {
    super.initState();
    _checkConnection();
  }

  Future<void> _checkConnection() async {
    try {
      final bool serverConnected = await _odooService.testServerConnection();
      print('Server connection test: ${serverConnected ? 'Success' : 'Failed'}');

      final bool apiConnected = await _odooService.testApiConnection();
      print('API connection test: ${apiConnected ? 'Success' : 'Failed'}');

      if (!serverConnected) {
        _showSnackBar('Unable to connect to server. Please check server address and internet connection.');
      }
    } catch (e) {
      print('Connection test error: $e');
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.black87,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }

  Future<void> _loginUser() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    _showSnackBar('Signing you in...');

    try {
      print('Login attempt with:');
      print('Username: ${_usernameController.text}');
      print('Password: ${_passwordController.text.replaceAll(RegExp(r'.'), '*')}');

      final success = await _odooService.loginWithService();

      if (success) {
        print('Service login successful, authenticating employee...');

        final employee = await _odooService.authenticateEmployee(
          _usernameController.text,
          _passwordController.text,
        );

        if (employee != null) {
          print('Employee authenticated successfully: ${employee.name}');

          if (!mounted) return;
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => HomePage(
                odooService: _odooService,
                employee: employee,
              ),
            ),
          );
        } else {
          _showSnackBar('Invalid username or password');
        }
      } else {
        _showSnackBar('Unable to connect to server');
      }
    } catch (e) {
      print('Login error: $e');
      _showSnackBar('An error occurred: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // ألوان حديثة وجذابة
    const gradientColors = [
      Color(0xFFE0EAFC), // أبيض مزرق
      Color(0xFFCFDEF3), // أزرق ثلجي
      Color(0xFF4F8CFF), // أزرق عصري
      Color(0xFFB568FF), // بنفسجي فاتح
      Color(0xFF43E97B), // أخضر نعناع عصري
    ];

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFFE0EAFC),
              Color(0xFFCFDEF3),
              Color(0xFFe8f0fe),
              Color(0xFFF9F6FF),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // الشعار
                  Container(
                    width: 112,
                    height: 112,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.08),
                          blurRadius: 18,
                          offset: const Offset(0, 8),
                        ),
                      ],
                      border: Border.all(
                        color: Colors.white.withOpacity(0.20),
                        width: 3,
                      ),
                    ),
                    child: Center(
                      child: Icon(
                        Icons.badge_outlined,
                        size: 56,
                        color: Color(0xFF4F8CFF).withOpacity(0.90),
                        shadows: [
                          Shadow(
                            color: Colors.blue.withOpacity(0.16),
                            blurRadius: 18,
                            offset: const Offset(1, 5),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),

                  // الكارت الزجاجي (Glass Card)
                  Container(
                    padding: const EdgeInsets.all(28),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.70),
                      borderRadius: BorderRadius.circular(26),
                      boxShadow: [
                        BoxShadow(
                          color: Color(0xFF4F8CFF).withOpacity(0.08),
                          blurRadius: 22,
                          offset: const Offset(0, 10),
                        ),
                      ],
                      border: Border.all(
                        color: Color(0xFF4F8CFF).withOpacity(0.13),
                        width: 1.2,
                      ),
                    ),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          // Username
                          TextFormField(
                            controller: _usernameController,
                            style: TextStyle(
                                color: Colors.grey[900],
                                fontWeight: FontWeight.w600),
                            cursorColor: Color(0xFF4F8CFF),
                            decoration: InputDecoration(
                              prefixIcon: Icon(Icons.person_outline, color: Color(0xFF4F8CFF).withOpacity(0.85)),
                              filled: true,
                              fillColor: Colors.white.withOpacity(0.9),
                              hintText: 'Username',
                              hintStyle: TextStyle(
                                color: Colors.grey[500],
                                letterSpacing: 1.1,
                              ),
                              contentPadding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide: BorderSide(
                                  color: Colors.white.withOpacity(0.15),
                                  width: 1.2,
                                ),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide: BorderSide(
                                  color: Colors.white.withOpacity(0.15),
                                  width: 1.2,
                                ),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide: BorderSide(
                                  color: Color(0xFF4F8CFF),
                                  width: 1.9,
                                ),
                              ),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter your username';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 18),

                          // Password
                          TextFormField(
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            style: TextStyle(
                                color: Colors.grey[900],
                                fontWeight: FontWeight.w600),
                            cursorColor: Color(0xFF4F8CFF),
                            decoration: InputDecoration(
                              prefixIcon: Icon(Icons.lock_outline, color: Color(0xFFB568FF).withOpacity(0.85)),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_off : Icons.visibility,
                                  color: Colors.grey[600],
                                ),
                                onPressed: () {
                                  setState(() {
                                    _obscurePassword = !_obscurePassword;
                                  });
                                },
                              ),
                              filled: true,
                              fillColor: Colors.white.withOpacity(0.9),
                              hintText: 'Password',
                              hintStyle: TextStyle(
                                color: Colors.grey[500],
                                letterSpacing: 1.2,
                              ),
                              contentPadding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide: BorderSide(
                                  color: Colors.white.withOpacity(0.15),
                                  width: 1.2,
                                ),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide: BorderSide(
                                  color: Colors.white.withOpacity(0.15),
                                  width: 1.2,
                                ),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide: BorderSide(
                                  color: Color(0xFFB568FF),
                                  width: 1.9,
                                ),
                              ),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter your password';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 12),

                          // Remember me
                          Row(
                            children: [
                              Checkbox(
                                value: _rememberMe,
                                onChanged: (value) {
                                  setState(() {
                                    _rememberMe = value ?? false;
                                  });
                                },
                                checkColor: Colors.white,
                                activeColor: Color(0xFF4F8CFF),
                                side: BorderSide(
                                  color: Color(0xFF4F8CFF).withOpacity(0.6),
                                  width: 1.3,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(5),
                                ),
                              ),
                              Text(
                                'Remember me',
                                style: TextStyle(
                                  color: Colors.grey[800],
                                  fontSize: 15,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 22),

                          // زر الدخول العصري
                          Container(
                            width: double.infinity,
                            height: 54,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(16),
                              gradient: _isLoading
                                  ? const LinearGradient(
                                colors: [
                                  Color(0xFFb1bfd8), // رمادي أزرق عند التحميل
                                  Color(0xFF6782B4),
                                ],
                              )
                                  : const LinearGradient(
                                colors: [
                                  Color(0xFF4F8CFF), // أزرق عصري
                                  Color(0xFFB568FF), // بنفسجي فاتح
                                  Color(0xFF43E97B), // أخضر نعناع عصري
                                ],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Color(0xFF4F8CFF).withOpacity(0.13),
                                  blurRadius: 13,
                                  offset: const Offset(0, 7),
                                ),
                              ],
                            ),
                            child: ElevatedButton(
                              onPressed: _isLoading ? null : _loginUser,
                              style: ElevatedButton.styleFrom(
                                elevation: 0,
                                backgroundColor: Colors.transparent, // الزر شفاف
                                foregroundColor: Colors.white,
                                shadowColor: Colors.transparent,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                padding: EdgeInsets.zero,
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                width: 28,
                                height: 28,
                                child: CircularProgressIndicator(
                                  strokeWidth: 3,
                                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                ),
                              )
                                  : const Text(
                                'LOGIN',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 1.6,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 38),

                  // Powered by
                  Opacity(
                    opacity: 0.92,
                    child: Text(
                      'Powered BY ERP Accounting and Auditing',
                      style: TextStyle(
                        color: Color(0xFF4F8CFF),
                        fontSize: 15,
                        letterSpacing: 1.2,
                        fontWeight: FontWeight.w600,
                        shadows: [
                          Shadow(
                            color: Colors.white.withOpacity(0.33),
                            blurRadius: 9,
                            offset: const Offset(1, 1),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
