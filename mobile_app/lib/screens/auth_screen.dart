import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';

class AuthScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;

  const AuthScreen({super.key, required this.onLoginSuccess});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isSignUp = false;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleAuth() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final email = _emailController.text.trim();
      final password = _passwordController.text.trim();

      if (email.isEmpty || password.isEmpty) {
        throw "Please enter both your email address and password.";
      }

      if (_isSignUp) {
        await SupabaseService().signUpWithEmail(email, password);
      } else {
        await SupabaseService().signInWithEmail(email, password);
      }
      widget.onLoginSuccess();
    } catch (e) {
      setState(() {
        _errorMessage = ErrorHandler.parseError(e);
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      body: SafeArea(
        child: Stack(
          children: [
            // Ambient Radial Glow Backdrop
            Positioned.fill(
              child: Container(
                decoration: const BoxDecoration(
                  radialGradient: RadialGradient(
                    center: Alignment(0, 0.8),
                    radius: 0.9,
                    colors: [
                      Color(0x358B5CF6), // rgba(139,92,246,0.21)
                      Color(0x2006B6D4), // rgba(6,182,212,0.12)
                      AppTheme.darkBackground,
                    ],
                  ),
                ),
              ),
            ),

            Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Official Web Portal Emblem & Brand Header
                    const TradingAILogo(size: 56),
                    const SizedBox(height: 14),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text(
                          "StokVigil ",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.5,
                          ),
                        ),
                        ShaderMask(
                          shaderCallback: (bounds) => AppTheme.logoGradient.createShader(bounds),
                          child: const Text(
                            "AI",
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      "Track Your Stocks. Spot the Signals.",
                      style: TextStyle(
                        color: AppTheme.cyan,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.4,
                      ),
                    ),
                    const SizedBox(height: 32),

                    // Glassmorphic Auth Card Matching Web Portal
                    GlassCard(
                      borderColor: AppTheme.borderCyan,
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _isSignUp ? "Create Free Account" : "Sign In to StokVigil AI",
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _isSignUp
                                ? "Receive real-time 5-min AI catalyst & profit alerts"
                                : "Enter your registered credentials to access radar",
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 20),

                          if (_errorMessage != null) ...[
                            Container(
                              padding: const EdgeInsets.all(12),
                              margin: const EdgeInsets.only(bottom: 16),
                              decoration: BoxDecoration(
                                color: AppTheme.dangerRose.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: AppTheme.dangerRose),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.error_outline, color: AppTheme.dangerRose, size: 18),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      _errorMessage!,
                                      style: const TextStyle(
                                        color: AppTheme.dangerRose,
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],

                          // Email Address Field
                          const Text(
                            "EMAIL ADDRESS",
                            style: TextStyle(
                              color: AppTheme.textMuted,
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.8,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Container(
                            decoration: BoxDecoration(
                              color: const Color(0xFF080B16),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppTheme.cardBorder),
                            ),
                            child: TextField(
                              controller: _emailController,
                              keyboardType: TextInputType.emailAddress,
                              style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                              decoration: const InputDecoration(
                                hintText: "investor@example.com",
                                hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                                border: InputBorder.none,
                                contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                prefixIcon: Icon(Icons.email_outlined, color: AppTheme.cyan, size: 20),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // Password Field
                          const Text(
                            "PASSWORD",
                            style: TextStyle(
                              color: AppTheme.textMuted,
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.8,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Container(
                            decoration: BoxDecoration(
                              color: const Color(0xFF080B16),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppTheme.cardBorder),
                            ),
                            child: TextField(
                              controller: _passwordController,
                              obscureText: true,
                              style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                              decoration: const InputDecoration(
                                hintText: "••••••••",
                                hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                                border: InputBorder.none,
                                contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                prefixIcon: Icon(Icons.lock_outline, color: AppTheme.cyan, size: 20),
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // Primary Gradient CTA Button
                          Container(
                            width: double.infinity,
                            height: 50,
                            decoration: BoxDecoration(
                              gradient: AppTheme.logoGradient,
                              borderRadius: BorderRadius.circular(14),
                              boxShadow: const [
                                BoxShadow(
                                  color: Color(0x4D06B6D4),
                                  blurRadius: 16,
                                  offset: Offset(0, 4),
                                ),
                              ],
                            ),
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.transparent,
                                shadowColor: Colors.transparent,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                              ),
                              onPressed: _isLoading ? null : _handleAuth,
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 22,
                                      width: 22,
                                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                                    )
                                  : Text(
                                      _isSignUp ? "Sign Up Free" : "Sign In",
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w900,
                                        fontSize: 16,
                                      ),
                                    ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // Toggle Sign In / Sign Up Link
                          Center(
                            child: TextButton(
                              onPressed: () {
                                setState(() {
                                  _isSignUp = !_isSignUp;
                                  _errorMessage = null;
                                });
                              },
                              child: Text(
                                _isSignUp
                                    ? "Already have an account? Sign In"
                                    : "Don't have an account? Sign Up Free",
                                style: const TextStyle(
                                  color: AppTheme.cyan,
                                  fontWeight: FontWeight.w900,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
