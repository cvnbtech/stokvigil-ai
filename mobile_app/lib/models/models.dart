class UserProfile {
  final String id;
  final String email;
  final String? fcmDeviceToken;
  final String? telegramChatId;
  final bool telegramEnabled;
  final bool dematAutoSync;

  UserProfile({
    required this.id,
    required this.email,
    this.fcmDeviceToken,
    this.telegramChatId,
    required this.telegramEnabled,
    this.dematAutoSync = false,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] ?? '',
      email: json['email'] ?? '',
      fcmDeviceToken: json['fcm_device_token'],
      telegramChatId: json['telegram_chat_id'],
      telegramEnabled: json['telegram_enabled'] ?? false,
      dematAutoSync: json['demat_auto_sync'] ?? false,
    );
  }
}

class PortfolioHolding {
  final String symbol;
  final String? name;
  final String? exchange;
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
  String get cleanSymbol => symbol.replaceAll('.BO', '').replaceAll('.NS', '').trim().toUpperCase();
  String get exch => exchange ?? (symbol.toUpperCase().endsWith('.BO') ? 'BSE' : 'NSE');
  String get displayName => (name != null && name!.isNotEmpty && name != symbol && !name!.endsWith('.BO')) ? name! : cleanSymbol;

  PortfolioHolding({
    required this.symbol,
    this.name,
    this.exchange,
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
    final sym = (json['clean_symbol'] ?? json['symbol'] ?? '').toString();
    return PortfolioHolding(
      symbol: sym,
      name: json['name'] ?? json['stock_name'],
      exchange: json['exchange'],
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

  String get cleanSymbol => symbol.replaceAll('.BO', '').replaceAll('.NS', '').trim().toUpperCase();
  String get exchange => metricsSnapshot['exchange'] ?? (symbol.toUpperCase().endsWith('.BO') ? 'BSE' : 'NSE');
  String get companyName => metricsSnapshot['company_name'] ?? metricsSnapshot['stock_name'] ?? cleanSymbol;
  String get actionBias => metricsSnapshot['action_bias'] ?? 'HOLD_NEUTRAL';
  Map<String, dynamic> get tacticalLevels => Map<String, dynamic>.from(metricsSnapshot['tactical_levels'] ?? {});
  String? get entryRange => tacticalLevels['entry_range'];
  String? get target1 => tacticalLevels['target_1'];
  String? get target2 => tacticalLevels['target_2'];
  String? get stopLoss => tacticalLevels['protective_stop_loss'];
  String? get riskReward => tacticalLevels['risk_reward_ratio'];
  Map<String, dynamic>? get dematPosition => metricsSnapshot['demat_position'] != null ? Map<String, dynamic>.from(metricsSnapshot['demat_position']) : null;
  Map<String, int>? get factorBreakdown {
    if (metricsSnapshot['factor_breakdown'] != null) {
      final fb = Map<String, dynamic>.from(metricsSnapshot['factor_breakdown']);
      if (fb.containsKey('technicals') && fb.containsKey('flow')) {
        return {
          'technicals': ((fb['technicals'] ?? 0) as num).toInt(),
          'flow': ((fb['flow'] ?? 0) as num).toInt(),
          'forensics': ((fb['forensics'] ?? 0) as num).toInt(),
          'catalysts': ((fb['catalysts'] ?? 0) as num).toInt(),
        };
      }
    }
    return null;
  }

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
