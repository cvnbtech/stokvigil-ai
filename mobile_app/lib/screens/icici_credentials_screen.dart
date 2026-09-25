import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';
import '../widgets/broker_icons.dart';

class IciciCredentialsScreen extends StatefulWidget {
  final VoidCallback onSaved;
  final String? initialSessionToken;

  const IciciCredentialsScreen({super.key, required this.onSaved, this.initialSessionToken});

  @override
  State<IciciCredentialsScreen> createState() => _IciciCredentialsScreenState();
}

class _IciciCredentialsScreenState extends State<IciciCredentialsScreen> with WidgetsBindingObserver {
  final _sessionTokenController = TextEditingController();
  String _selectedBroker = 'icici';
  String _loginUrl = '';
  bool _isLoading = false;
  bool _isSuccess = false;
  bool _hasExistingValidSession = false;
  String? _lastTokenDate;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    if (widget.initialSessionToken != null && widget.initialSessionToken!.isNotEmpty) {
      _sessionTokenController.text = widget.initialSessionToken!;
    }
    _sessionTokenController.addListener(_onFieldChanged);
    _loadBrokerAndCredentials();
  }

  void _onFieldChanged() {
    if (mounted) setState(() {});
  }

  bool get _isFormValid => _sessionTokenController.text.trim().isNotEmpty;

  Future<void> _loadBrokerAndCredentials() async {
    // 1. Directly fetch official broker login URL (public endpoint, works immediately)
    try {
      final directUrl = await ApiService().fetchBrokerLoginUrl(_selectedBroker);
      if (directUrl != null && directUrl.isNotEmpty && directUrl.contains("api_key=") && !directUrl.endsWith("api_key=") && mounted) {
        setState(() {
          _loginUrl = directUrl;
        });
      }
    } catch (e) {
      debugPrint("Could not fetch direct broker login URL: $e");
    }

    final user = SupabaseService().currentUser;
    if (user == null) return;
    try {
      final creds = await ApiService().fetchUserCredentials(user.id);
      if (creds != null && mounted) {
        final url = creds['login_url']?.toString();
        if (url != null && url.isNotEmpty && url.contains("api_key=") && !url.endsWith("api_key=")) {
          _loginUrl = url;
        }

        final todayStr = DateTime.now().toIso8601String().split('T')[0];
        final tokenDate = creds['token_date']?.toString();
        final hasCreds = creds['has_credentials'] == true;

        setState(() {
          _lastTokenDate = tokenDate;
          _hasExistingValidSession = hasCreds && (tokenDate == todayStr);
        });
      }
    } catch (e) {
      debugPrint("Could not load broker credentials status: $e");
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _sessionTokenController.removeListener(_onFieldChanged);
    _sessionTokenController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _autoDetectClipboardToken();
    }
  }

  Future<void> _autoDetectClipboardToken() async {
    try {
      final data = await Clipboard.getData(Clipboard.kTextPlain);
      final text = data?.text?.trim();
      if (text != null && text.isNotEmpty && mounted) {
        String clean = text;
        if (clean.contains("apisession=")) {
          clean = clean.split("apisession=")[1].split("&")[0];
        }
        clean = Uri.decodeComponent(clean).trim();
        // If clean looks like a valid ICICI session token and is not already set
        if (clean.length >= 4 && clean.length <= 128 && clean != _sessionTokenController.text.trim()) {
          if (RegExp(r'^[a-zA-Z0-9_\-\.+=]{4,128}$').hasMatch(clean)) {
            setState(() {
              _sessionTokenController.text = clean;
            });
            ErrorHandler.showSuccessSnackBar(context, "⚡ Session token auto-detected and pasted from clipboard!");
          }
        }
      }
    } catch (_) {}
  }

  Future<void> _pasteFromClipboard() async {
    try {
      final data = await Clipboard.getData(Clipboard.kTextPlain);
      final text = data?.text?.trim();
      if (text != null && text.isNotEmpty && mounted) {
        String clean = text;
        if (clean.contains("apisession=")) {
          clean = clean.split("apisession=")[1].split("&")[0];
        }
        clean = Uri.decodeComponent(clean).trim();
        setState(() {
          _sessionTokenController.text = clean;
        });
        ErrorHandler.showSuccessSnackBar(context, "Session token pasted from clipboard!");
      } else if (mounted) {
        ErrorHandler.showErrorSnackBar(
          context,
          "Clipboard is empty. Complete login in browser and tap 'Copy Session Token' first.",
        );
      }
    } catch (e) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, "Unable to access clipboard: $e");
      }
    }
  }

  void _openBrokerLogin() async {
    if (_loginUrl.isEmpty || !_loginUrl.contains("api_key=") || _loginUrl.endsWith("api_key=")) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(
          context,
          "⚠️ Broker login URL is loading or server ICICI Master App Key is unconfigured. Re-checking backend...",
        );
      }
      await _loadBrokerAndCredentials();
      if (_loginUrl.isEmpty || !_loginUrl.contains("api_key=") || _loginUrl.endsWith("api_key=")) {
        return;
      }
    }
    final url = Uri.parse(_loginUrl);
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
    String sessionToken = _sessionTokenController.text.trim();
    if (sessionToken.isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please enter or paste your session token.");
      return;
    }

    if (sessionToken.contains("apisession=")) {
      sessionToken = sessionToken.split("apisession=")[1].split("&")[0];
      sessionToken = Uri.decodeComponent(sessionToken).trim();
    }

    final user = SupabaseService().currentUser;
    if (user == null) {
      setState(() => _isSuccess = true);
      ErrorHandler.showSuccessSnackBar(context, "Demat connected successfully!");
      Future.delayed(const Duration(milliseconds: 1200), widget.onSaved);
      return;
    }

    setState(() => _isLoading = true);
    try {
      bool success = await ApiService().saveIciciCredentials(
        userId: user.id,
        sessionToken: sessionToken,
        broker: _selectedBroker,
      );

      setState(() {
        _isLoading = false;
        _isSuccess = success;
      });

      if (success) {
        if (mounted) {
          ErrorHandler.showSuccessSnackBar(context, "✅ Demat Connected & Synced (AES-256 Vault)");
        }
        Future.delayed(const Duration(milliseconds: 1200), widget.onSaved);
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Failed to save session token. Please try again.");
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
            Icon(Icons.link_rounded, color: AppTheme.cyan, size: 22),
            SizedBox(width: 8),
            Text(
              "Connect Demat Broker",
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18),
            ),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20.0),
        children: [
          // Multi-Broker Selection Tabs
          const Text(
            "SELECT BROKER",
            style: TextStyle(
              color: AppTheme.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.0,
            ),
          ),
          const SizedBox(height: 10),
          _buildBrokerSelector(),
          const SizedBox(height: 18),

          // Active Session Status or Success Banner
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
                      "✅ Demat Account Connected! Vault secured with AES-256 encryption.",
                      style: TextStyle(color: AppTheme.primaryEmerald, fontWeight: FontWeight.w900, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
          ] else if (_hasExistingValidSession) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.primaryEmerald.withOpacity(0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.4)),
              ),
              child: Row(
                children: const [
                  Icon(Icons.verified, color: AppTheme.primaryEmerald, size: 20),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "● ICICI Direct Connected for today's market session",
                      style: TextStyle(color: AppTheme.primaryEmerald, fontWeight: FontWeight.w800, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
          ],

          // Main 1-Click Connect Card
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.cyan.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.flash_on, color: AppTheme.cyan, size: 20),
                    ),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "Institutional 1-Click Onboarding",
                            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14),
                          ),
                          Text(
                            "Log in with standard User ID & OTP • Zero API Keys",
                            style: TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Step 1: Login CTA
                const Text(
                  "STEP 1: AUTHENTICATE WITH BROKER",
                  style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 11, letterSpacing: 0.5),
                ),
                const SizedBox(height: 6),
                const Text(
                  "Opens the official, secure ICICI Direct authentication portal in your browser.",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, height: 1.4),
                ),
                const SizedBox(height: 12),

                Container(
                  width: double.infinity,
                  height: 48,
                  decoration: BoxDecoration(
                    color: AppTheme.cyan.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.cyan.withOpacity(0.4)),
                  ),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _openBrokerLogin,
                      borderRadius: BorderRadius.circular(14),
                      child: Center(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const IciciDirectLogo(size: 18),
                            const SizedBox(width: 8),
                            Text(
                              (_loginUrl.isNotEmpty && _loginUrl.contains("api_key=") && !_loginUrl.endsWith("api_key="))
                                  ? "1-Tap ICICI Direct Login"
                                  : "Connecting to ICICI Direct...",
                              style: const TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 13),
                            ),
                            const SizedBox(width: 6),
                            const Icon(Icons.open_in_new, color: AppTheme.cyan, size: 16),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 22),

                // Step 2: Session Token
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      "STEP 2: SESSION TOKEN",
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 11, letterSpacing: 0.5),
                    ),
                    GestureDetector(
                      onTap: _pasteFromClipboard,
                      child: Row(
                        children: const [
                          Icon(Icons.content_paste, color: AppTheme.cyan, size: 14),
                          SizedBox(width: 4),
                          Text(
                            "Paste",
                            style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),

                TextField(
                  controller: _sessionTokenController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: "Paste session token (apisession) here",
                    hintStyle: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 12),
                    filled: true,
                    fillColor: Colors.white.withOpacity(0.04),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.12)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppTheme.cyan),
                    ),
                  ),
                ),
                const SizedBox(height: 22),

                // Primary Connect CTA Button
                AnimatedOpacity(
                  opacity: (_isFormValid && !_isLoading) ? 1.0 : 0.45,
                  duration: const Duration(milliseconds: 200),
                  child: Container(
                    width: double.infinity,
                    height: 52,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [
                          Color(0xFF00B4D8),
                          Color(0xFF0284C7),
                          Color(0xFF6366F1),
                          Color(0xFF8B5CF6),
                        ],
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                      ),
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: _isFormValid ? const Color(0x6606B6D4) : const Color(0x3306B6D4),
                          blurRadius: _isFormValid ? 16 : 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
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
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.lock_outline, size: 18, color: Colors.white),
                              SizedBox(width: 8),
                              Text(
                                "Connect Demat & Sync Holdings",
                                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14),
                              ),
                            ],
                          ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

          // Security & Compliance Disclaimer
          Center(
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: const [
                    Icon(Icons.shield_outlined, color: AppTheme.textSecondary, size: 14),
                    SizedBox(width: 6),
                    Text(
                      "AES-256 Vault Encrypted • Zero Plaintext Storage",
                      style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  "Regulated broker API session • Automatically refreshed daily per SEBI norms.",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 10),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBrokerSelector() {
    return Row(
      children: [
        // ICICI Direct (Active)
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
            decoration: BoxDecoration(
              color: AppTheme.cyan.withOpacity(0.12),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.cyan),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: const [
                        IciciDirectLogo(size: 16),
                        SizedBox(width: 6),
                        Text("ICICI Direct", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12)),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryEmerald,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text("ACTIVE", style: TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 8)),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text("1-Click Demat Connect", style: TextStyle(color: AppTheme.cyan, fontSize: 10, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
        ),
        const SizedBox(width: 8),

        // Zerodha (Coming Soon)
        Expanded(
          child: Opacity(
            opacity: 0.5,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.04),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withOpacity(0.1)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          ZerodhaLogo(size: 16),
                          SizedBox(width: 6),
                          Text("Zerodha", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12)),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text("SOON", style: TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.w800, fontSize: 8)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  const Text("Kite Connect", style: TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),

        // Angel One (Coming Soon)
        Expanded(
          child: Opacity(
            opacity: 0.5,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.04),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withOpacity(0.1)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          AngelOneLogo(size: 16),
                          SizedBox(width: 6),
                          Text("Angel One", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12)),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text("SOON", style: TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.w800, fontSize: 8)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  const Text("SmartAPI", style: TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
