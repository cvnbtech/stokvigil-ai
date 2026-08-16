import 'package:flutter/material.dart';
import '../config/theme.dart';

class TermsConditionsModal extends StatefulWidget {
  final VoidCallback onAccept;

  const TermsConditionsModal({super.key, required this.onAccept});

  @override
  State<TermsConditionsModal> createState() => _TermsConditionsModalState();
}

class _TermsConditionsModalState extends State<TermsConditionsModal> {
  final ScrollController _scrollController = ScrollController();
  bool _hasScrolledToBottom = false;
  double _scrollProgress = 0.0;

  final List<Map<String, String>> _sections = const [
    {
      "title": "1. Service Description",
      "body":
          "StokVigil AI is a market intelligence and research watchtower platform. It monitors your ICICI Direct demat holdings every 5 minutes and delivers factual catalyst notifications (block deals, earnings beats, quarterly P&L, debt shifts) during Indian market hours (09:15 AM – 03:30 PM IST, Mon–Fri)."
    },
    {
      "title": "2. Zero SEBI Advisory & No Automated Trades",
      "body":
          "StokVigil AI is NOT registered with SEBI as an Investment Advisor. All information provided is strictly 100% factual market data. We do NOT recommend buying, selling, or holding any securities. We do NOT execute automated trades on your behalf. All investment decisions remain 100% in your control."
    },
    {
      "title": "3. Credential Security & Vault Storage",
      "body":
          "Your ICICI Breeze API credentials (App Key, Secret Key, Session Token) are encrypted client-side using AES-256 Fernet cipher with SHA-256 PBKDF2 key derivation before vault storage in Supabase PostgreSQL with Row-Level Security (RLS) enabled."
    },
    {
      "title": "4. Market Risk Disclaimer",
      "body":
          "Equity market investments carry inherent financial risk. Past performance of any stock, catalyst, or pattern does not guarantee future results. You may lose part or all of your invested capital. Only invest capital you can afford to lose."
    },
    {
      "title": "5. Data Privacy Guarantee",
      "body":
          "We do not sell, rent, or share your personal or demat data with third parties. Your credentials are used strictly to retrieve your personal portfolio positions for monitoring."
    },
    {
      "title": "6. User Agreement & Account Termination",
      "body":
          "By creating an account, you confirm that you have read, understood, and agreed to these terms. You may delete your account and revoke API access at any time."
    },
  ];

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.position.pixels;
    
    setState(() {
      _scrollProgress = (maxScroll > 0) ? (currentScroll / maxScroll).clamp(0.0, 1.0) : 1.0;
      if (currentScroll >= maxScroll - 40) {
        _hasScrolledToBottom = true;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.cardBackground,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: const BorderSide(color: AppTheme.borderCyan, width: 1.5),
      ),
      child: Container(
        height: MediaQuery.of(context).size.height * 0.75,
        constraints: const BoxConstraints(maxHeight: 580),
        child: Column(
          children: [
            // Fixed Header Row
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: const BoxDecoration(
                color: Color(0xFF0A0E1A),
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                border: Border(bottom: BorderSide(color: AppTheme.cardBorder)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "📄 Terms & Conditions",
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16),
                        ),
                        SizedBox(height: 2),
                        Text(
                          "StokVigil AI • Updated August 2026",
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close, color: AppTheme.textSecondary, size: 20),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
            ),

            // Scroll Progress Indicator Bar
            LinearProgressIndicator(
              value: _scrollProgress,
              backgroundColor: const Color(0xFF080B16),
              color: AppTheme.cyan,
              minHeight: 3,
            ),

            // Scrollable Legal Sections
            Expanded(
              child: Scrollbar(
                controller: _scrollController,
                child: ListView.separated(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(20),
                  itemCount: _sections.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 16),
                  itemBuilder: (context, index) {
                    final item = _sections[index];
                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: const Color(0xFF080B16),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppTheme.cardBorder),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item["title"]!,
                            style: const TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            item["body"]!,
                            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12, height: 1.45),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ),

            // Footer Acceptance Button
            Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                color: Color(0xFF0A0E1A),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(24)),
                border: Border(top: BorderSide(color: AppTheme.cardBorder)),
              ),
              child: Column(
                children: [
                  if (!_hasScrolledToBottom) ...[
                    const Text(
                      "👇 Scroll down to read all terms before accepting",
                      style: TextStyle(color: AppTheme.textMuted, fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                  ],
                  Container(
                    width: double.infinity,
                    height: 48,
                    decoration: BoxDecoration(
                      gradient: _hasScrolledToBottom ? AppTheme.logoGradient : null,
                      color: _hasScrolledToBottom ? null : AppTheme.cardBorder,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: _hasScrolledToBottom
                          ? () {
                              Navigator.of(context).pop();
                              widget.onAccept();
                            }
                          : null,
                      child: Text(
                        "I Have Read & Accept Terms",
                        style: TextStyle(
                          color: _hasScrolledToBottom ? Colors.white : AppTheme.textMuted,
                          fontWeight: FontWeight.w900,
                          fontSize: 14,
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
    );
  }
}
