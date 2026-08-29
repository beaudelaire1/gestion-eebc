/// Modèle représentant une demande de transport assignée au chauffeur.
class TransportRequest {
  final int id;
  final String requesterName;
  final String requesterPhone;
  final String pickupAddress;
  final DateTime eventDate;
  final String eventTime;
  final String eventName;
  final int passengersCount;
  final String status;
  final bool isTrackingActive;

  const TransportRequest({
    required this.id,
    required this.requesterName,
    required this.requesterPhone,
    required this.pickupAddress,
    required this.eventDate,
    required this.eventTime,
    required this.eventName,
    required this.passengersCount,
    required this.status,
    required this.isTrackingActive,
  });

  factory TransportRequest.fromJson(Map<String, dynamic> json) {
    return TransportRequest(
      id: json['id'] as int,
      requesterName: json['requesterName'] as String? ?? '',
      requesterPhone: json['requesterPhone'] as String? ?? '',
      pickupAddress: json['pickupAddress'] as String? ?? '',
      eventDate: DateTime.parse(json['eventDate'] as String),
      eventTime: json['eventTime'] as String? ?? '',
      eventName: json['eventName'] as String? ?? '',
      passengersCount: json['passengersCount'] as int? ?? 1,
      status: json['status'] as String? ?? 'pending',
      isTrackingActive: json['isTrackingActive'] as bool? ?? false,
    );
  }

  String get statusLabel {
    switch (status) {
      case 'confirmed':
        return 'Confirmé';
      case 'pending':
        return 'En attente';
      case 'completed':
        return 'Terminé';
      case 'cancelled':
        return 'Annulé';
      default:
        return status;
    }
  }
}

/// Modèle de la position live renvoyée par l'API.
class LiveLocationData {
  final bool hasLocation;
  final double? latitude;
  final double? longitude;
  final double? speedKmh;
  final double? accuracyM;
  final double? headingDeg;
  final bool isActive;
  final bool stale;
  final int? ageSeconds;

  const LiveLocationData({
    required this.hasLocation,
    this.latitude,
    this.longitude,
    this.speedKmh,
    this.accuracyM,
    this.headingDeg,
    required this.isActive,
    required this.stale,
    this.ageSeconds,
  });

  factory LiveLocationData.fromJson(Map<String, dynamic> json) {
    return LiveLocationData(
      hasLocation: json['has_location'] as bool? ?? false,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      speedKmh: (json['speed_kmh'] as num?)?.toDouble(),
      accuracyM: (json['accuracy_m'] as num?)?.toDouble(),
      headingDeg: (json['heading_deg'] as num?)?.toDouble(),
      isActive: json['is_active'] as bool? ?? false,
      stale: json['stale'] as bool? ?? false,
      ageSeconds: json['age_seconds'] as int?,
    );
  }
}
