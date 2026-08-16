import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../services/fcm_service.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';
import 'icici_credentials_screen.dart';

class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() => _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState extends State<NotificationSettingsScreen> {
  final _telegramChatIdController = TextEditingController();
  bool _telegramEnabled = true;
  bool _fcmEnabled = true;
  String _alertSensitivity = 'HIGH';
  String _executionWorkflow = 'CONFIRM'; // 'INSTANT' vs 'CONFIRM'
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadNotificationSettings();
  }

  Future<void> _loadNotificationSettings() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    try {
      final data = await SupabaseService().client
          .from('profiles')
          .select()
          .eq('id', user.id)
          .single();

      setState(() {
        _telegramChatIdController.text = data['telegram_chat_id'] ?? '';
        _telegramEnabled = data['telegram_enabled'] ?? true;
        _fcmEnabled = data['fcm_enabled'] ?? true;
        _alertSensitivity = (data['alert_sensitivity'] ?? 'HIGH').toString().toUpperCase();
        _executionWorkflow = (data['execution_mode'] ?? 'INSTANT').toString().toUpperCase();
      });
    } catch (e) {
      debugPrint("Error loading profile settings: $e");
    }
  }

  Future<void> _saveSettingsSilently() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;
    try {
      final fcmToken = FcmService().fcmToken;
      await ApiService().registerDeviceToken(
        userId: user.id,
        fcmToken: fcmToken,
        fcmEnabled: _fcmEnabled,
        telegramChatId: _telegramChatIdController.text.trim(),
        telegramEnabled: _telegramEnabled,
        alertSensitivity: _alertSensitivity,
        executionMode: _executionWorkflow,
      );
    } catch (e) {
      debugPrint("Auto-save settings error: $e");
    }
  }

  Future<void> _saveSettings() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      ErrorHandler.showSuccessSnackBar(context, "Settings saved locally!");
      return;
    }

    setState(() => _isSaving = true);
    try {
      final fcmToken = FcmService().fcmToken;

      final success = await ApiService().registerDeviceToken(
        userId: user.id,
        fcmToken: fcmToken,
        fcmEnabled: _fcmEnabled,
        telegramChatId: _telegramChatIdController.text.trim(),
        telegramEnabled: _telegramEnabled,
        alertSensitivity: _alertSensitivity,
        executionMode: _executionWorkflow,
      );

      setState(() => _isSaving = false);

      if (mounted) {
        if (success) {
          ErrorHandler.showSuccessSnackBar(context, "Preferences saved successfully!");
        } else {
          ErrorHandler.showErrorSnackBar(context, "Server unreachable. Failed to update preferences.");
        }
      }
    } catch (e) {
      setState(() => _isSaving = false);
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  Future<void> _signOutUser() async {
    try {
      await SupabaseService().signOut();
      if (mounted) {
        ErrorHandler.showSuccessSnackBar(context, "Signed out successfully.");
      }
    } catch (e) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  void _openTelegramBot() async {
    try {
      final user = SupabaseService().currentUser;
      final email = user?.email ?? 'investor@gmail.com';
      final url = Uri.parse("https://t.me/StokVigilBot?start=$email");
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Unable to launch Telegram. Please ensure Telegram app is installed.");
        }
      }
    } catch (e) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  void _navigateToIciciConfig() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => IciciCredentialsScreen(
          onSaved: () {
            if (mounted) {
              ErrorHandler.showSuccessSnackBar(context, "ICICI Breeze Session Key configured!");
            }
          },
        ),
      ),
    );
  }

  Future<void> _showChangePasswordModal() async {
    final newPasswordController = TextEditingController();
    bool isUpdating = false;
    bool isDone = false;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Dialog(
          backgroundColor: AppTheme.cardBackground,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(22),
            side: const BorderSide(color: AppTheme.borderCyan, width: 1.5),
          ),
          child: Container(
            padding: const EdgeInsets.all(22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      "🔑 Change Password",
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close, color: AppTheme.textSecondary, size: 20),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                if (isDone) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryEmerald.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.primaryEmerald),
                    ),
                    child: const Text(
                      "✅ Password changed successfully!",
                      style: TextStyle(color: AppTheme.primaryEmerald, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                  Container(
                    width: double.infinity,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: AppTheme.logoGradient,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text("Done", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                    ),
                  ),
                ] else ...[
                  const Text(
                    "Please enter your new password below (at least 6 characters):",
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, height: 1.4),
                  ),
                  const SizedBox(height: 14),
                  Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFF080B16),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.cardBorder),
                    ),
                    child: TextField(
                      controller: newPasswordController,
                      obscureText: true,
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                      decoration: const InputDecoration(
                        hintText: "New Password",
                        hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        prefixIcon: Icon(Icons.lock_outline, color: AppTheme.cyan, size: 18),
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Container(
                    width: double.infinity,
                    height: 46,
                    decoration: BoxDecoration(
                      gradient: AppTheme.logoGradient,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: isUpdating
                          ? null
                          : () async {
                              final newPass = newPasswordController.text.trim();
                              if (newPass.length < 6) {
                                ErrorHandler.showErrorSnackBar(context, "Password must be at least 6 characters.");
                                return;
                              }

                              setModalState(() => isUpdating = true);
                              try {
                                if (SupabaseService.isConfigured) {
                                  await SupabaseService().client.auth.updateUser(
                                    UserAttributes(password: newPass),
                                  );
                                }
                                setModalState(() {
                                  isUpdating = false;
                                  isDone = true;
                                });
                              } catch (e) {
                                setModalState(() => isUpdating = false);
                                if (mounted) ErrorHandler.showErrorSnackBar(context, e);
                              }
                            },
                      child: isUpdating
                          ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Text("Save New Password →", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        title: const StokVigilBrandHeader(),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        children: [
          // ─────────────────────────────────────────────
          // USER PROFILE HEADER CARD
          // ─────────────────────────────────────────────
          Builder(
            builder: (context) {
              final user = SupabaseService().currentUser;
              final email = user?.email ?? 'investor@gmail.com';
              final username = email.contains('@') ? email.split('@')[0] : email;
              final initial = username.isNotEmpty ? username[0].toUpperCase() : 'U';

              return GlassCard(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFF38BDF8), Color(0xFF8B5CF6)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Center(
                            child: Text(
                              initial,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                                fontSize: 20,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              username,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              email,
                              style: const TextStyle(
                                color: AppTheme.cyan,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    IconButton(
                      tooltip: "Sign Out",
                      icon: const Icon(Icons.logout_rounded, color: AppTheme.dangerRose, size: 22),
                      onPressed: _signOutUser,
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 18),

          // ─────────────────────────────────────────────
          // SECTION 1: BROKER INTEGRATION & API
          // ─────────────────────────────────────────────
          _buildSectionHeader("🔌 BROKER INTEGRATION & API"),
          const SizedBox(height: 8),

          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ICICI Breeze Key Card
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.cyan.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppTheme.borderCyan),
                          ),
                          child: const Text("🔑", style: TextStyle(fontSize: 18)),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text("ICICI Breeze Session Key", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                            SizedBox(height: 2),
                            Text("Required daily — expires at midnight IST", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                          ],
                        ),
                      ],
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.cyan.withOpacity(0.15),
                        foregroundColor: AppTheme.cyan,
                        side: const BorderSide(color: AppTheme.borderCyan),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                      onPressed: _navigateToIciciConfig,
                      child: const Text("Configure Key →", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11)),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Divider(color: AppTheme.cardBorder),
                const SizedBox(height: 8),

                // DEFAULT EXECUTION WORKFLOW
                const Text("⚡ DEFAULT EXECUTION WORKFLOW", style: TextStyle(color: AppTheme.textSecondary, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 0.6)),
                const SizedBox(height: 10),

                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          setState(() => _executionWorkflow = 'INSTANT');
                          _saveSettingsSilently();
                        },
                        child: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: _executionWorkflow == 'INSTANT' ? AppTheme.cyan.withOpacity(0.15) : AppTheme.cardBackground2,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: _executionWorkflow == 'INSTANT' ? AppTheme.cyan : AppTheme.cardBorder),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "⚡ Instant Execution",
                                style: TextStyle(
                                  color: _executionWorkflow == 'INSTANT' ? AppTheme.cyan : Colors.white,
                                  fontWeight: FontWeight.w900,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(height: 2),
                              const Text("1-Tap Direct Breeze Order", style: TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          setState(() => _executionWorkflow = 'CONFIRM');
                          _saveSettingsSilently();
                        },
                        child: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: _executionWorkflow == 'CONFIRM' ? AppTheme.violet.withOpacity(0.18) : AppTheme.cardBackground2,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: _executionWorkflow == 'CONFIRM' ? AppTheme.violet : AppTheme.cardBorder),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "🛡️ Confirm First",
                                style: TextStyle(
                                  color: _executionWorkflow == 'CONFIRM' ? const Color(0xFFC084FC) : Colors.white,
                                  fontWeight: FontWeight.w900,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(height: 2),
                              const Text("Review parameters first", style: TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ─────────────────────────────────────────────
          // SECTION 2: REAL-TIME NOTIFICATIONS
          // ─────────────────────────────────────────────
          _buildSectionHeader("🔔 REAL-TIME NOTIFICATIONS"),
          const SizedBox(height: 8),

          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Telegram Card
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.cyan.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppTheme.borderCyan),
                          ),
                          child: const Text("✈️", style: TextStyle(fontSize: 18)),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text("Telegram Bot Channel", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                            SizedBox(height: 2),
                            Text("Instant catalyst & order alerts", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                          ],
                        ),
                      ],
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.cyan.withOpacity(0.15),
                        foregroundColor: AppTheme.cyan,
                        side: const BorderSide(color: AppTheme.borderCyan),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                      onPressed: _openTelegramBot,
                      child: const Text("Connect @StokVigilBot", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11)),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Divider(color: AppTheme.cardBorder),
                const SizedBox(height: 8),

                // AI Alert Signal Frequency
                const Text("🔥 AI Alert Signal Frequency", style: TextStyle(color: AppTheme.textSecondary, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 0.6)),
                const SizedBox(height: 10),

                Row(
                  children: [
                    _buildSensitivityButton('HIGH', '🔥 High Impact'),
                    _buildSensitivityButton('ALL', '⚡ All Signals'),
                    _buildSensitivityButton('FII', '📊 FII / Institutional'),
                  ],
                ),
                const SizedBox(height: 14),
                const Divider(color: AppTheme.cardBorder),
                const SizedBox(height: 4),

                // Push Notification Alerts (FCM)
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  activeColor: AppTheme.cyan,
                  title: const Text("Push Notification Alerts (FCM)", style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: const Text("Receive 5-min market hours push alerts on phone", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                  value: _fcmEnabled,
                  onChanged: (val) {
                    setState(() => _fcmEnabled = val);
                    _saveSettingsSilently();
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ─────────────────────────────────────────────
          // SECTION 3: ACCOUNT SESSION
          // ─────────────────────────────────────────────
          _buildSectionHeader("🔒 ACCOUNT SESSION"),
          const SizedBox(height: 8),

          GlassCard(
            child: Column(
              children: [
                // Change Password Button Box
                GestureDetector(
                  onTap: _showChangePasswordModal,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppTheme.cardBackground2,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.cardBorder),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: const [
                        Row(
                          children: [
                            Text("🔑 ", style: TextStyle(fontSize: 14)),
                            Text("Change Password", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13)),
                          ],
                        ),
                        Icon(Icons.arrow_forward, color: AppTheme.textSecondary, size: 16),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Sign Out Container Button
                GestureDetector(
                  onTap: _signOutUser,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: AppTheme.dangerRose.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.dangerRose.withOpacity(0.6)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(Icons.logout, color: AppTheme.dangerRose, size: 18),
                        SizedBox(width: 8),
                        Text(
                          "Sign Out",
                          style: TextStyle(
                            color: AppTheme.dangerRose,
                            fontWeight: FontWeight.w900,
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(
        color: AppTheme.textMuted,
        fontSize: 11,
        fontWeight: FontWeight.w900,
        letterSpacing: 0.8,
      ),
    );
  }

  Widget _buildSensitivityButton(String mode, String label) {
    final active = _alertSensitivity == mode;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _alertSensitivity = mode);
          _saveSettingsSilently();
        },
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 3),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: active ? AppTheme.cyan.withOpacity(0.15) : AppTheme.cardBackground2,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: active ? AppTheme.cyan : AppTheme.cardBorder),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                color: active ? AppTheme.cyan : AppTheme.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
