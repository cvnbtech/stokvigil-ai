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
          .maybeSingle();

      if (data != null && mounted) {
        setState(() {
          _telegramChatIdController.text = data['telegram_chat_id'] ?? '';
          _telegramEnabled = data['telegram_enabled'] ?? true;
          _fcmEnabled = data['fcm_enabled'] ?? true;
          _alertSensitivity = (data['alert_sensitivity'] ?? 'HIGH').toString().toUpperCase();
          _executionWorkflow = (data['execution_mode'] ?? 'INSTANT').toString().toUpperCase();
        });
      }
    } catch (e) {
      debugPrint("Error loading profile settings: $e");
    }
  }

  Future<void> _saveSettingsSilently() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;
    try {
      final fcmToken = FcmService().fcmToken ?? await FcmService().getDeviceToken();
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
      final startParam = user?.id ?? (user?.email?.replaceAll(RegExp(r'[^a-zA-Z0-9_]'), '_') ?? 'user');
      final url = Uri.parse("https://t.me/StokVigilAi_bot?start=$startParam");
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
                      boxShadow: const [
                        BoxShadow(color: Color(0x4D06B6D4), blurRadius: 10, offset: Offset(0, 4)),
                      ],
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

  void _showDeleteAccountDialog() {
    final user = SupabaseService().currentUser;
    final confirmController = TextEditingController();
    bool isDeleting = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setModalState) => Dialog(
          backgroundColor: const Color(0xFF0D111E),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: const BorderSide(color: AppTheme.dangerRose, width: 1.5),
          ),
          child: Padding(
            padding: const EdgeInsets.all(22.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.warning_amber_rounded, color: AppTheme.dangerRose, size: 28),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        "Delete Account Permanently?",
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                const Text(
                  "This action is permanent and cannot be undone. All of the following data will be erased immediately:",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, height: 1.4),
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.dangerRose.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.dangerRose.withOpacity(0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text("• All personal watchlists and synced stocks", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11.5)),
                      SizedBox(height: 4),
                      Text("• Encrypted ICICI Breeze API & Session keys", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11.5)),
                      SizedBox(height: 4),
                      Text("• Telegram bot bindings & device tokens", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11.5)),
                      SizedBox(height: 4),
                      Text("• Your login credentials and account identity", style: TextStyle(color: AppTheme.dangerRose, fontSize: 11.5, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                RichText(
                  text: const TextSpan(
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                    children: [
                      TextSpan(text: "To confirm, please type "),
                      TextSpan(
                        text: "DELETE",
                        style: TextStyle(color: AppTheme.dangerRose, fontWeight: FontWeight.w900),
                      ),
                      TextSpan(text: " below:"),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF080B16),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.cardBorder),
                  ),
                  child: TextField(
                    controller: confirmController,
                    autofocus: true,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                    decoration: const InputDecoration(
                      hintText: "Type DELETE to confirm",
                      hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      border: InputBorder.none,
                    ),
                    onChanged: (val) => setModalState(() {}),
                  ),
                ),
                const SizedBox(height: 22),
                Builder(
                  builder: (context) {
                    final isConfirmed = confirmController.text.trim() == "DELETE";
                    return Row(
                      children: [
                        // CANCEL BUTTON
                        Expanded(
                          child: Container(
                            height: 48,
                            decoration: BoxDecoration(
                              color: const Color(0xFF131A2B),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: const Color(0xFF2A364F), width: 1.2),
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                borderRadius: BorderRadius.circular(14),
                                onTap: isDeleting ? null : () => Navigator.of(dialogContext).pop(),
                                child: const Center(
                                  child: Text(
                                    "Cancel",
                                    style: TextStyle(
                                      color: Color(0xFF94A3B8),
                                      fontWeight: FontWeight.w800,
                                      fontSize: 13.5,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),

                        // DELETE ACCOUNT BUTTON
                        Expanded(
                          child: Container(
                            height: 48,
                            decoration: BoxDecoration(
                              gradient: isConfirmed
                                  ? const LinearGradient(
                                      colors: [
                                        Color(0xFFEF4444),
                                        Color(0xFFDC2626),
                                        Color(0xFFB91C1C),
                                      ],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    )
                                  : null,
                              color: isConfirmed ? null : const Color(0xFF201318),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: isConfirmed ? const Color(0xFFF87171) : const Color(0xFF4A1D24),
                                width: 1.2,
                              ),
                              boxShadow: isConfirmed
                                  ? const [
                                      BoxShadow(
                                        color: Color(0x66EF4444),
                                        blurRadius: 16,
                                        offset: Offset(0, 4),
                                      ),
                                    ]
                                  : null,
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                borderRadius: BorderRadius.circular(14),
                                onTap: (!isConfirmed || isDeleting)
                                    ? null
                                    : () async {
                                        setModalState(() => isDeleting = true);
                                        if (user != null) {
                                          await ApiService().deleteUserAccount(user.id);
                                          await SupabaseService().deleteAccountCascade();
                                        }
                                        await SupabaseService().signOut();
                                        if (mounted) {
                                          Navigator.of(dialogContext).pop();
                                          ErrorHandler.showSuccessSnackBar(
                                            context,
                                            "✅ Your account and all associated data have been permanently deleted.",
                                          );
                                        }
                                      },
                                child: Center(
                                  child: isDeleting
                                      ? const SizedBox(
                                          height: 20,
                                          width: 20,
                                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.2),
                                        )
                                      : Text(
                                          "Delete Account",
                                          style: TextStyle(
                                            color: isConfirmed ? Colors.white : const Color(0xFF8B3A44),
                                            fontWeight: FontWeight.w900,
                                            fontSize: 13.5,
                                          ),
                                        ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
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
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Row(
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
                          const SizedBox(width: 12),
                          Flexible(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  username,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w900,
                                    fontSize: 16,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  email,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: AppTheme.cyan,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
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
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Row(
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
                          const SizedBox(width: 10),
                          Flexible(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: const [
                                Text(
                                  "ICICI Breeze Session Key",
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  "Required daily — expires at midnight IST",
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 10.5),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      height: 36,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [
                            Color(0xFF00B4D8),
                            Color(0xFF6366F1),
                            Color(0xFF8B5CF6),
                          ],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                        ),
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: const [
                          BoxShadow(
                            color: Color(0x4406B6D4),
                            blurRadius: 8,
                            offset: Offset(0, 2),
                          ),
                        ],
                      ),
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.transparent,
                          shadowColor: Colors.transparent,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                        ),
                        onPressed: _navigateToIciciConfig,
                        child: const Text("Setup Key →", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 11)),
                      ),
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
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Container(
                            width: 38,
                            height: 38,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [Color(0xFF2AABEE), Color(0xFF229ED9)],
                                begin: Alignment.topRight,
                                end: Alignment.bottomLeft,
                              ),
                              borderRadius: BorderRadius.circular(11),
                              boxShadow: [
                                BoxShadow(
                                  color: const Color(0xFF229ED9).withOpacity(0.35),
                                  blurRadius: 10,
                                  offset: const Offset(0, 3),
                                ),
                              ],
                            ),
                            child: Center(
                              child: Transform.translate(
                                offset: const Offset(-1.5, 1.5),
                                child: Transform.rotate(
                                  angle: -0.42,
                                  child: const Icon(
                                    Icons.send_rounded,
                                    color: Colors.white,
                                    size: 19,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Flexible(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: const [
                                Text(
                                  "Telegram Bot Channel",
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  "Instant catalyst & order alerts",
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 10.5),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.cyan.withOpacity(0.15),
                        foregroundColor: AppTheme.cyan,
                        side: const BorderSide(color: AppTheme.borderCyan),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                      onPressed: _openTelegramBot,
                      child: const Text("Connect →", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11)),
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
                  subtitle: Text(
                    _fcmEnabled ? "Receive 5-min market hours push alerts on phone" : "Push notifications paused",
                    style: TextStyle(color: _fcmEnabled ? AppTheme.textSecondary : AppTheme.textMuted, fontSize: 11),
                  ),
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
          // SECTION 3: SECURITY & ACCESS
          // ─────────────────────────────────────────────
          _buildSectionHeader("🔒 SECURITY & ACCESS"),
          const SizedBox(height: 10),

          GlassCard(
            child: GestureDetector(
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
          ),
          const SizedBox(height: 18),

          // ─────────────────────────────────────────────
          // SECTION 4: DANGER ZONE (DELETE ACCOUNT)
          // ─────────────────────────────────────────────
          _buildSectionHeader("⚠️ DANGER ZONE"),
          const SizedBox(height: 10),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Delete Account & Data",
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5),
                ),
                const SizedBox(height: 4),
                const Text(
                  "Permanently erase your account, watchlist, and encrypted broker keys.",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                ),
                const SizedBox(height: 14),
                GestureDetector(
                  onTap: _showDeleteAccountDialog,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: AppTheme.dangerRose.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.dangerRose.withOpacity(0.6)),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.delete_forever_rounded, color: AppTheme.dangerRose, size: 18),
                        SizedBox(width: 8),
                        Text(
                          "Delete My Account",
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
          const SizedBox(height: 20),

          // ─────────────────────────────────────────────
          // BOTTOM ACTION: SIGN OUT (GRADIENT PILL CTA)
          // ─────────────────────────────────────────────
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
              onPressed: _signOutUser,
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.logout_rounded, color: Colors.white, size: 19),
                  SizedBox(width: 8),
                  Text(
                    "Sign Out",
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 15,
                      letterSpacing: -0.2,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
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
