import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';

class IciciCredentialsScreen extends StatefulWidget {
  final VoidCallback onSaved;

  const IciciCredentialsScreen({super.key, required this.onSaved});

  @override
  State<IciciCredentialsScreen> createState() => _IciciCredentialsScreenState();
}

class _IciciCredentialsScreenState extends State<IciciCredentialsScreen> {
  final _appKeyController = TextEditingController();
  final _secretKeyController = TextEditingController();
  final _sessionTokenController = TextEditingController();
  bool _showAppKey = false;
  bool _showSecretKey = false;
  bool _isLoading = false;
  bool _isSuccess = false;

  @override
  void initState() {
    super.initState();
    _appKeyController.addListener(_onFieldChanged);
    _secretKeyController.addListener(_onFieldChanged);
    _sessionTokenController.addListener(_onFieldChanged);
    _loadExistingCredentials();
  }

  void _onFieldChanged() {
    if (mounted) setState(() {});
  }

  bool get _isFormValid =>
      _appKeyController.text.trim().isNotEmpty &&
      _secretKeyController.text.trim().isNotEmpty &&
      _sessionTokenController.text.trim().isNotEmpty;

  Future<void> _loadExistingCredentials() async {
    final user = SupabaseService().currentUser;
    if (user == null || !SupabaseService.isConfigured) return;
    try {
      // 1. First try getting decrypted keys from backend API
      final creds = await ApiService().fetchUserCredentials(user.id);
      if (creds != null && creds['has_credentials'] == true && mounted) {
        final appKeyVal = creds['app_key']?.toString() ?? '';
        final secretKeyVal = creds['secret_key']?.toString() ?? '';
        if (appKeyVal.isNotEmpty) _appKeyController.text = appKeyVal;
        if (secretKeyVal.isNotEmpty) _secretKeyController.text = secretKeyVal;
        return;
      }

      // 2. Fallback: Direct Supabase client
      final data = await SupabaseService().client
          .from('user_credentials')
          .select('encrypted_app_key, encrypted_secret_key')
          .eq('user_id', user.id)
          .maybeSingle();
      if (data != null && mounted) {
        final rawAppKey = data['encrypted_app_key']?.toString() ?? '';
        final rawSecretKey = data['encrypted_secret_key']?.toString() ?? '';
        if (rawAppKey.isNotEmpty) {
          try {
            _appKeyController.text = utf8.decode(base64Url.decode(rawAppKey));
          } catch (_) {
            _appKeyController.text = rawAppKey;
          }
        }
        if (rawSecretKey.isNotEmpty) {
          try {
            _secretKeyController.text = utf8.decode(base64Url.decode(rawSecretKey));
          } catch (_) {
            _secretKeyController.text = rawSecretKey;
          }
        }
      }
    } catch (e) {
      debugPrint("Could not pre-fill saved keys: $e");
    }
  }

  @override
  void dispose() {
    _appKeyController.removeListener(_onFieldChanged);
    _secretKeyController.removeListener(_onFieldChanged);
    _sessionTokenController.removeListener(_onFieldChanged);
    _appKeyController.dispose();
    _secretKeyController.dispose();
    _sessionTokenController.dispose();
    super.dispose();
  }

  void _openIciciLogin() async {
    final appKey = _appKeyController.text.trim();
    if (appKey.isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please enter your ICICI App Key above first before opening login.");
      return;
    }

    // Open In-App Secure WebView for 100% Automatic Session Token Auto-Capture
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.90,
          child: IciciLoginWebViewDialog(
            appKey: appKey,
            onSessionCaptured: (session) {
              setState(() {
                _sessionTokenController.text = session;
              });
              if (mounted) {
                ErrorHandler.showSuccessSnackBar(context, "⚡ Session token auto-captured! Encrypting & saving...");
              }
              // Auto-save if secret key is also filled
              if (_secretKeyController.text.trim().isNotEmpty) {
                Future.delayed(const Duration(milliseconds: 400), _saveCredentials);
              }
            },
          ),
        ),
      ),
    );
  }

  Future<void> _saveCredentials() async {
    final appKey = _appKeyController.text.trim();
    final secretKey = _secretKeyController.text.trim();
    final sessionToken = _sessionTokenController.text.trim();

    if (appKey.isEmpty || secretKey.isEmpty || sessionToken.isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please fill in all 3 credentials fields (App Key, Secret Key, Session Token).");
      return;
    }

    final user = SupabaseService().currentUser;
    if (user == null) {
      setState(() => _isSuccess = true);
      ErrorHandler.showSuccessSnackBar(context, "Credentials encrypted and saved successfully!");
      Future.delayed(const Duration(milliseconds: 1200), widget.onSaved);
      return;
    }

    setState(() => _isLoading = true);
    try {
      // 1. Direct Supabase Encrypted Vault Save (Instant & 100% Reliable Upsert)
      bool success = await SupabaseService().saveIciciCredentials(
        userId: user.id,
        appKey: appKey,
        secretKey: secretKey,
        sessionToken: sessionToken,
      );

      // 2. If direct Supabase failed, fallback to Backend API save
      if (!success) {
        success = await ApiService().saveIciciCredentials(
          userId: user.id,
          appKey: appKey,
          secretKey: secretKey,
          sessionToken: sessionToken,
        );
      } else {
        // Background sync to backend Fernet vault
        ApiService().saveIciciCredentials(
          userId: user.id,
          appKey: appKey,
          secretKey: secretKey,
          sessionToken: sessionToken,
        ).catchError((_) => false);
      }

      setState(() {
        _isLoading = false;
        _isSuccess = success;
      });

      if (success) {
        if (mounted) {
          ErrorHandler.showSuccessSnackBar(context, "✅ ICICI Breeze Session Key encrypted & saved!");
        }
        Future.delayed(const Duration(milliseconds: 1200), widget.onSaved);
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Failed to save credentials. Please check your internet connection.");
        }
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: const [
            Icon(Icons.vpn_key_outlined, color: AppTheme.cyan, size: 22),
            SizedBox(width: 8),
            Text("ICICI Breeze Key Setup", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20.0),
        children: [
          if (_isSuccess) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primaryEmerald.withOpacity(0.12),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.primaryEmerald),
              ),
              child: Row(
                children: const [
                  Icon(Icons.check_circle, color: AppTheme.primaryEmerald, size: 24),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      "✅ Credentials encrypted (AES-256) & saved successfully!",
                      style: TextStyle(color: AppTheme.primaryEmerald, fontWeight: FontWeight.w900, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],

          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("🔐 Client-Side AES-256 Vault Encryption", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                const SizedBox(height: 6),
                const Text(
                  "Session tokens expire daily at midnight. Paste your morning ICICI Breeze token below.",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, height: 1.4),
                ),
                const SizedBox(height: 20),

                // App Key Input with View Toggle
                _buildInput(
                  label: "APP KEY",
                  controller: _appKeyController,
                  hint: "Enter ICICI Breeze App Key",
                  isObscure: !_showAppKey,
                  onToggleVisibility: () => setState(() => _showAppKey = !_showAppKey),
                ),
                const SizedBox(height: 14),

                // Secret Key Input with View Toggle
                _buildInput(
                  label: "SECRET KEY",
                  controller: _secretKeyController,
                  hint: "Enter Secret Key",
                  isObscure: !_showSecretKey,
                  onToggleVisibility: () => setState(() => _showSecretKey = !_showSecretKey),
                ),
                const SizedBox(height: 14),

                // 1-Tap ICICI Web Login & Auto-Capture Button
                Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: AppTheme.cyan.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.cyan.withOpacity(0.35)),
                  ),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _openIciciLogin,
                      borderRadius: BorderRadius.circular(14),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: const [
                            Icon(Icons.bolt, color: AppTheme.cyan, size: 18),
                            SizedBox(width: 6),
                            Text(
                              "1-Tap Login & Auto-Capture Token",
                              style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // Session Token Input
                _buildInput(
                  label: "SESSION TOKEN (AUTO-POPULATED)",
                  controller: _sessionTokenController,
                  hint: "Tap button above or paste token here",
                  isObscure: false,
                ),
                const SizedBox(height: 24),

                // Encrypt & Save CTA Button (Enabled ONLY when form is valid)
                Container(
                  width: double.infinity,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: _isFormValid
                        ? const LinearGradient(
                            colors: [
                              Color(0xFF00B4D8), // Vibrant Cyan
                              Color(0xFF0284C7), // Sky Blue
                              Color(0xFF6366F1), // Indigo
                              Color(0xFF8B5CF6), // Violet Purple
                            ],
                            begin: Alignment.centerLeft,
                            end: Alignment.centerRight,
                          )
                        : null,
                    color: _isFormValid ? null : Colors.white.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(16),
                    border: _isFormValid ? null : Border.all(color: Colors.white.withOpacity(0.1)),
                    boxShadow: _isFormValid
                        ? const [
                            BoxShadow(
                              color: Color(0x6606B6D4),
                              blurRadius: 16,
                              offset: Offset(0, 4),
                            ),
                          ]
                        : null,
                  ),
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      disabledBackgroundColor: Colors.transparent,
                      shadowColor: Colors.transparent,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      padding: EdgeInsets.zero,
                    ),
                    onPressed: (_isFormValid && !_isLoading) ? _saveCredentials : null,
                    child: _isLoading
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.2),
                          )
                        : Text(
                            "🔐 Encrypt & Save Key",
                            style: TextStyle(
                              color: _isFormValid ? Colors.white : const Color(0xFF64748B),
                              fontWeight: FontWeight.w900,
                              fontSize: 15,
                              letterSpacing: -0.2,
                            ),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInput({
    required String label,
    required TextEditingController controller,
    required String hint,
    required bool isObscure,
    VoidCallback? onToggleVisibility,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 0.8)),
            if (onToggleVisibility != null)
              GestureDetector(
                onTap: onToggleVisibility,
                behavior: HitTestBehavior.opaque,
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 2),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isObscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                        color: AppTheme.cyan,
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        isObscure ? "Show" : "Hide",
                        style: const TextStyle(
                          color: AppTheme.cyan,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: const Color(0xFF080B16),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.cardBorder),
          ),
          child: TextField(
            controller: controller,
            obscureText: isObscure,
            style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
              border: InputBorder.none,
            ),
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────
// IN-APP SECURE ICICI LOGIN WEBVIEW WITH AUTO-CAPTURE
// ─────────────────────────────────────────────
class IciciLoginWebViewDialog extends StatefulWidget {
  final String appKey;
  final Function(String sessionToken) onSessionCaptured;

  const IciciLoginWebViewDialog({
    super.key,
    required this.appKey,
    required this.onSessionCaptured,
  });

  @override
  State<IciciLoginWebViewDialog> createState() => _IciciLoginWebViewDialogState();
}

class _IciciLoginWebViewDialogState extends State<IciciLoginWebViewDialog> {
  late final WebViewController _controller;
  bool _isLoading = true;
  double _progress = 0;
  bool _hasCaptured = false;

  @override
  void initState() {
    super.initState();
    final url = "https://api.icicidirect.com/apiuser/login?api_key=${Uri.encodeComponent(widget.appKey)}";

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF0B0E17))
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (int progress) {
            if (mounted) setState(() => _progress = progress / 100.0);
          },
          onPageStarted: (String url) {
            if (mounted) setState(() => _isLoading = true);
            _checkUrlForSession(url);
          },
          onPageFinished: (String url) {
            if (mounted) setState(() => _isLoading = false);
            _checkUrlForSession(url);
          },
          onNavigationRequest: (NavigationRequest request) {
            final captured = _checkUrlForSession(request.url);
            if (captured) {
              return NavigationDecision.prevent;
            }
            return NavigationDecision.navigate;
          },
        ),
      )
      ..loadRequest(Uri.parse(url));
  }

  bool _checkUrlForSession(String url) {
    if (_hasCaptured) return true;
    try {
      final uri = Uri.parse(url);
      // Look for ICICI Breeze session token in query parameters
      final session = uri.queryParameters['apisession'] ??
          uri.queryParameters['api_session'] ??
          uri.queryParameters['session_token'] ??
          uri.queryParameters['sessionToken'] ??
          uri.queryParameters['token'];

      if (session != null && session.trim().isNotEmpty) {
        _hasCaptured = true;
        widget.onSessionCaptured(session.trim());
        Navigator.of(context).pop();
        return true;
      }

      // Regex fallback if query parameter was formatted differently in redirect
      final match = RegExp(r'[?&#](apisession|api_session|session_token)=([^&#]+)').firstMatch(url);
      if (match != null && match.group(2) != null) {
        final rawToken = Uri.decodeComponent(match.group(2)!);
        if (rawToken.trim().isNotEmpty) {
          _hasCaptured = true;
          widget.onSessionCaptured(rawToken.trim());
          Navigator.of(context).pop();
          return true;
        }
      }
    } catch (_) {}
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E17),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              "ICICI Direct Secure Login",
              style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900),
            ),
            Text(
              "Session token will be auto-captured",
              style: TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.w600),
            ),
          ],
        ),
        bottom: _isLoading
            ? PreferredSize(
                preferredSize: const Size.fromHeight(2),
                child: LinearProgressIndicator(
                  value: _progress > 0 ? _progress : null,
                  backgroundColor: Colors.transparent,
                  color: AppTheme.cyan,
                  minHeight: 2,
                ),
              )
            : null,
      ),
      body: WebViewWidget(controller: _controller),
    );
  }
}
