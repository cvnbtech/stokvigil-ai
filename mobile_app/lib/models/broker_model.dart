class BrokerInfo {
  final String id;
  final String name;
  final String status;
  final String authType;
  final String loginUrl;
  final String description;

  const BrokerInfo({
    required this.id,
    required this.name,
    required this.status,
    required this.authType,
    required this.loginUrl,
    required this.description,
  });

  bool get isActive => status == 'active';

  factory BrokerInfo.fromJson(Map<String, dynamic> json) {
    return BrokerInfo(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      status: json['status']?.toString() ?? 'coming_soon',
      authType: json['auth_type']?.toString() ?? 'session_token',
      loginUrl: json['login_url']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
    );
  }
}
