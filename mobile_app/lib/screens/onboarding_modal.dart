import 'package:flutter/material.dart';
import '../config/theme.dart';

class OnboardingDisclaimerModal extends StatelessWidget {
  final VoidCallback onAccept;

  const OnboardingDisclaimerModal({super.key, required this.onAccept});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.cardBackground,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryEmerald.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.shield_outlined, color: AppTheme.primaryEmerald, size: 28),
                ),
                const SizedBox(width: 14),
                const Expanded(
                  child: Text(
                    "StokVigil AI Commitment",
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(width: 0, height: 20),
            const Text(
              "StokVigil AI is an automated, unsleeping market watchtower.",
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
            ),
            const SizedBox(height: 12),
            _buildBullet("Pure Factual Intelligence", "Delivers real-time data alerts on catalysts, quarterly results, block deals, and valuation shifts."),
            _buildBullet("Zero Automated Trades", "The app never places trades or executes buy/sell orders on your demat account."),
            _buildBullet("Non-Advisory Guarantee", "StokVigil AI does not provide SEBI-registered financial tips or target recommendations. 100% of trading decisions remain yours."),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryEmerald,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: onAccept,
                child: const Text("I Understand & Agree", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 15)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBullet(String title, String desc) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle_outline, color: AppTheme.primaryEmerald, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, height: 1.4),
                children: [
                  TextSpan(text: "$title: ", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  TextSpan(text: desc),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
