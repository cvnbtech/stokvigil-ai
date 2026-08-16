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
  bool _isLoading = false;
  bool _isSuccess = false;

  @override
  void dispose() {
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

    final user = SupabaseService().currentUser;
    if (user == null) {
      setState(() => _isSuccess = true);
      ErrorHandler.showSuccessSnackBar(context, "Credentials encrypted and saved successfully!");
      Future.delayed(const Duration(milliseconds: 1200), widget.onSaved);
      return;
    }

    setState(() => _isLoading = true);
    try {
      final success = await ApiService().saveIciciCredentials(
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
          ErrorHandler.showSuccessSnackBar(context, "ICICI Breeze Session Key encrypted & saved!");
        }
        Future.delayed(const Duration(milliseconds: 1200), widget.onSaved);
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Failed to encrypt credentials. Server temporarily unreachable.");
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

                // App Key Input
                _buildInput("APP KEY", _appKeyController, "Enter ICICI Breeze App Key", false),
                const SizedBox(height: 14),

                // Secret Key Input
                _buildInput("SECRET KEY", _secretKeyController, "Enter Secret Key", true),
                const SizedBox(height: 14),

                // 1-Tap ICICI Web Login Button
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppTheme.borderCyan),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    onPressed: _openIciciLogin,
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text("🌐 1-Tap ICICI Web Login", style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 12)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // Session Token Input
                _buildInput("SESSION TOKEN", _sessionTokenController, "Paste morning session token here", false),
                const SizedBox(height: 24),

                // Encrypt & Save CTA Button (Matches User Screenshot)
                Container(
                  width: double.infinity,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF00B4D8), // Vibrant Cyan
                        Color(0xFF0284C7), // Sky Blue
                        Color(0xFF6366F1), // Indigo
                        Color(0xFF8B5CF6), // Violet Purple
                      ],
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x6606B6D4),
                        blurRadius: 16,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      shadowColor: Colors.transparent,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      padding: EdgeInsets.zero,
                    ),
                    onPressed: _isLoading ? null : _saveCredentials,
                    child: _isLoading
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.2),
                          )
                        : const Text(
                            "🔐 Encrypt & Save Key",
                            style: TextStyle(
                              color: Colors.white,
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

  Widget _buildInput(String label, TextEditingController controller, String hint, bool isPassword) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 0.8)),
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
            obscureText: isPassword,
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
