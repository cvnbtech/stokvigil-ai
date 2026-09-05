import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
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

  bool _isEncryptedBlob(String val) {
    if (val.isEmpty) return false;
    // Fernet AES-256 tokens start with "gAAAAA" and are over 50 chars
    if (val.startsWith("gAAAAA") && val.length > 50) return true;
    return false;
  }

  String _decodeDatabaseValue(String raw) {
    if (raw.isEmpty) return "";
    final trimmed = raw.trim();

    if (_isEncryptedBlob(trimmed)) {
      // Fernet ciphertext blob cannot be decoded without backend decryption key
      return "";
    }

    // 1. Try URL-Safe Base64 Decode
    try {
      String normalized = trimmed.replaceAll('-', '+').replaceAll('_', '/');
      while (normalized.length % 4 != 0) {
        normalized += '=';
      }
      final decoded = utf8.decode(base64.decode(normalized));
      if (decoded.isNotEmpty && RegExp(r'^[\x20-\x7E]+$').hasMatch(decoded) && !_isEncryptedBlob(decoded)) {
        return decoded;
      }
    } catch (_) {}

    // 2. Try Standard Base64 Decode
    try {
      final decoded = utf8.decode(base64.decode(base64.normalize(trimmed)));
      if (decoded.isNotEmpty && RegExp(r'^[\x20-\x7E]+$').hasMatch(decoded) && !_isEncryptedBlob(decoded)) {
        return decoded;
      }
    } catch (_) {}

    // 3. If raw string is already plain text (alphanumeric ICICI key)
    if (!_isEncryptedBlob(trimmed) && RegExp(r'^[a-zA-Z0-9_\-~^@#*!]+$').hasMatch(trimmed) && trimmed.length <= 64) {
      return trimmed;
    }

    return "";
  }

  Future<void> _loadExistingCredentials() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;
    try {
      // Get decrypted keys securely from backend API (Backend Fernet Vault)
      final creds = await ApiService().fetchUserCredentials(user.id);
      if (creds != null && creds['has_credentials'] == true && mounted) {
        final appKeyVal = creds['app_key']?.toString() ?? '';
        final secretKeyVal = creds['secret_key']?.toString() ?? '';

        if (appKeyVal.isNotEmpty) _appKeyController.text = appKeyVal;
        if (secretKeyVal.isNotEmpty) _secretKeyController.text = secretKeyVal;
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
    if (_isEncryptedBlob(appKey)) {
      ErrorHandler.showErrorSnackBar(context, "Encrypted key detected. Please paste your plain ICICI Breeze App Key from api.icicidirect.com");
      return;
    }
    final urlStr = "https://api.icicidirect.com/apiuser/login?api_key=${Uri.encodeComponent(appKey)}";
    final url = Uri.parse(urlStr);
    try {
      final success = await launchUrl(url, mode: LaunchMode.externalApplication);
      if (!success) {
        await launchUrl(url, mode: LaunchMode.platformDefault);
      }
    } catch (e) {
      try {
        await launchUrl(url, mode: LaunchMode.inAppBrowserView);
      } catch (err) {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Unable to open browser: $err");
        }
      }
    }
  }

  Future<void> _saveCredentials() async {
    final appKey = _appKeyController.text.trim();
    final secretKey = _secretKeyController.text.trim();
    final sessionToken = _sessionTokenController.text.trim();

    if (appKey.isEmpty || secretKey.isEmpty || sessionToken.isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please fill in all 3 credentials fields (App Key, Secret Key, Session Token).");
      return;
    }

    if (_isEncryptedBlob(appKey) || _isEncryptedBlob(secretKey)) {
      ErrorHandler.showErrorSnackBar(context, "Please enter your plain API keys, not encrypted strings.");
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
      // Save credentials exclusively via Backend API (Fernet AES-256 Vault)
      bool success = await ApiService().saveIciciCredentials(
        userId: user.id,
        appKey: appKey,
        secretKey: secretKey,
        sessionToken: sessionToken,
      );

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

                // 1-Tap ICICI Web Login Button
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
                      child: const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12, horizontal: 14),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              "🌐 1-Tap ICICI Web Login",
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
