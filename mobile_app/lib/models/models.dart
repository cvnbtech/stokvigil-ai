class UserProfile {
  final String id;
  final String email;
  final String? fcmDeviceToken;
  final String? telegramChatId;
  final bool telegramEnabled;

  UserProfile({
    required this.id,
    required this.email,
    this.fcmDeviceToken,
    this.telegramChatId,
    required this.telegramEnabled,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] ?? '',
      email: json['email'] ?? '',
      fcmDeviceToken: json['fcm_device_token'],
      telegramChatId: json['telegram_chat_id'],
      telegramEnabled: json['telegram_enabled'] ?? false,
    );
  }
}

class PortfolioHolding {
  final String symbol;
  final double quantity;
  final double avgPrice;
  final double currentPrice;
  final double currentValue;
  final double pnl;
  final double pnlPercent;
  final double? peRatio;
  final double? debtToEquity;

  double get currentVal => currentValue;
  double get pnlPct => pnlPercent;

  PortfolioHolding({
    required this.symbol,
    required this.quantity,
    required this.avgPrice,
    required this.currentPrice,
    double? currentValue,
    double? currentVal,
    required this.pnl,
    double? pnlPercent,
    double? pnlPct,
    this.peRatio,
    this.debtToEquity,
  })  : currentValue = currentValue ?? currentVal ?? 0.0,
        pnlPercent = pnlPercent ?? pnlPct ?? 0.0;

  factory PortfolioHolding.fromJson(Map<String, dynamic> json) {
    return PortfolioHolding(
      symbol: json['symbol'] ?? '',
      quantity: (json['quantity'] ?? 0).toDouble(),
      avgPrice: (json['avg_price'] ?? 0).toDouble(),
      currentPrice: (json['current_price'] ?? 0).toDouble(),
      currentValue: (json['current_value'] ?? json['current_val'] ?? 0).toDouble(),
      pnl: (json['pnl'] ?? 0).toDouble(),
      pnlPercent: (json['pnl_percent'] ?? json['pnl_pct'] ?? 0).toDouble(),
      peRatio: json['pe_ratio'] != null ? (json['pe_ratio']).toDouble() : null,
      debtToEquity: json['debt_to_equity'] != null ? (json['debt_to_equity']).toDouble() : null,
    );
  }
}

class StokAlert {
  final String id;
  final String? userId;
  final String symbol;
  final String alertTitle;
  final String catalystType;
  final int impactScore;
  final List<String> factualReasons;
  final Map<String, dynamic> metricsSnapshot;
  final bool sentViaFcm;
  final bool sentViaTelegram;
  final DateTime createdAt;

  StokAlert({
    required this.id,
    this.userId,
    required this.symbol,
    required this.alertTitle,
    String? catalystType,
    required this.impactScore,
    required this.factualReasons,
    required this.metricsSnapshot,
    bool? sentViaFcm,
    bool? sentViaTelegram,
    DateTime? createdAt,
  })  : catalystType = catalystType ?? 'NEWS_CATALYST',
        sentViaFcm = sentViaFcm ?? false,
        sentViaTelegram = sentViaTelegram ?? false,
        createdAt = createdAt ?? DateTime.now();

  factory StokAlert.fromJson(Map<String, dynamic> json) {
    return StokAlert(
      id: json['id'] ?? '',
      userId: json['user_id'],
      symbol: json['symbol'] ?? '',
      alertTitle: json['alert_title'] ?? '',
      catalystType: json['catalyst_type'] ?? 'NEWS_CATALYST',
      impactScore: json['impact_score'] ?? 50,
      factualReasons: List<String>.from(json['factual_reasons'] ?? []),
      metricsSnapshot: Map<String, dynamic>.from(json['metrics_snapshot'] ?? {}),
      sentViaFcm: json['sent_via_fcm'] ?? false,
      sentViaTelegram: json['sent_via_telegram'] ?? false,
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : DateTime.now(),
    );
  }
}
