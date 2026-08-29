import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import '../models/transport_request.dart';
import 'api_service.dart';

/// Service gérant le tracking GPS live pour le chauffeur.
///
/// - Fetch des courses assignées via GET /transport/my-requests/
/// - Stream de position GPS envoyé toutes les 10 secondes vers l'API
/// - Consultation de la position live via GET /transport/requests/<id>/live/status/
class TransportTrackingService extends ChangeNotifier {
  final ApiService _api;

  TransportTrackingService(this._api);

  // ── État ─────────────────────────────────────────────────────────────────

  List<TransportRequest> _myRequests = [];
  List<TransportRequest> get myRequests => List.unmodifiable(_myRequests);

  int? _activeRequestId;
  int? get activeRequestId => _activeRequestId;

  bool _isTracking = false;
  bool get isTracking => _isTracking;

  String? _error;
  String? get error => _error;

  bool _loading = false;
  bool get loading => _loading;

  // État de la dernière position envoyée
  double? _lastLat;
  double? _lastLng;
  double? _lastSpeedKmh;
  double? _lastAccuracy;
  double? get lastLat => _lastLat;
  double? get lastLng => _lastLng;
  double? get lastSpeedKmh => _lastSpeedKmh;
  double? get lastAccuracy => _lastAccuracy;

  StreamSubscription<Position>? _positionSub;
  Timer? _pushTimer;
  Position? _pendingPosition;

  // ── Permissions GPS ───────────────────────────────────────────────────────

  /// Vérifie et demande les permissions GPS. Retourne true si autorisé.
  Future<bool> checkAndRequestPermission() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      _setError('Le GPS est désactivé. Activez-le dans les paramètres.');
      return false;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      _setError('Permission GPS refusée. Autorisez l\'accès à la position.');
      return false;
    }
    return true;
  }

  // ── Courses du chauffeur ──────────────────────────────────────────────────

  /// Charge les courses assignées au chauffeur connecté.
  Future<void> fetchMyRequests() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _api.get('/transport/my-requests/');
      if (response['success'] == true) {
        final rawList = response['data'] as List<dynamic>;
        _myRequests = rawList
            .map((e) => TransportRequest.fromJson(e as Map<String, dynamic>))
            .toList();
      } else {
        _setError('Impossible de charger les courses.');
      }
    } catch (e) {
      _setError('Erreur réseau : $e');
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  // ── Démarrage du tracking ─────────────────────────────────────────────────

  /// Démarre l'envoi de position GPS pour la course [requestId].
  Future<bool> startTracking(int requestId) async {
    if (_isTracking) await stopTracking();

    final hasPermission = await checkAndRequestPermission();
    if (!hasPermission) return false;

    _activeRequestId = requestId;
    _isTracking = true;
    _error = null;
    notifyListeners();

    // Stream de position GPS haute précision
    const settings = LocationSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 5, // mètres
    );

    _positionSub = Geolocator.getPositionStream(locationSettings: settings).listen(
      (pos) {
        _pendingPosition = pos;
        _lastLat = pos.latitude;
        _lastLng = pos.longitude;
        _lastSpeedKmh = pos.speed >= 0 ? pos.speed * 3.6 : null;
        _lastAccuracy = pos.accuracy;
        notifyListeners();
      },
      onError: (dynamic err) {
        _setError('Erreur GPS : $err');
      },
    );

    // Timer d'envoi toutes les 10 secondes
    _pushTimer = Timer.periodic(const Duration(seconds: 10), (_) => _pushPosition());

    // Envoi immédiat si une position est déjà disponible
    Future.delayed(const Duration(seconds: 1), _pushPosition);

    return true;
  }

  /// Arrête le tracking GPS et signale is_active=false à l'API.
  Future<void> stopTracking() async {
    _pushTimer?.cancel();
    _pushTimer = null;
    await _positionSub?.cancel();
    _positionSub = null;

    final reqId = _activeRequestId;
    _isTracking = false;
    _activeRequestId = null;
    _pendingPosition = null;
    notifyListeners();

    if (reqId != null) {
      try {
        await _api.post('/transport/requests/$reqId/live/update/', {
          'latitude': _lastLat ?? 0,
          'longitude': _lastLng ?? 0,
          'is_active': false,
        });
      } catch (_) {
        // Ignorer l'erreur lors de l'arrêt
      }
    }
  }

  // ── Envoi position ────────────────────────────────────────────────────────

  Future<void> _pushPosition() async {
    final reqId = _activeRequestId;
    final pos = _pendingPosition;
    if (reqId == null || pos == null || !_isTracking) return;

    final payload = <String, dynamic>{
      'latitude': pos.latitude,
      'longitude': pos.longitude,
      'is_active': true,
    };
    if (pos.speed >= 0) payload['speed_kmh'] = pos.speed * 3.6;
    if (pos.accuracy > 0) payload['accuracy_m'] = pos.accuracy;
    if (pos.heading >= 0) payload['heading_deg'] = pos.heading;

    try {
      await _api.post('/transport/requests/$reqId/live/update/', payload);
    } catch (e) {
      // Pas critique — on réessaie au prochain tick
      debugPrint('TransportTracking push error: $e');
    }
  }

  // ── Consultation de position live ─────────────────────────────────────────

  /// Consulte la position live d'une course (lecture seule, passager/admin).
  Future<LiveLocationData?> fetchLiveStatus(int requestId) async {
    try {
      final response = await _api.get('/transport/requests/$requestId/live/status/');
      if (response['success'] == true && response['data'] != null) {
        return LiveLocationData.fromJson(response['data'] as Map<String, dynamic>);
      }
    } catch (e) {
      debugPrint('TransportTracking status error: $e');
    }
    return null;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  void _setError(String msg) {
    _error = msg;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  @override
  Future<void> dispose() async {
    _pushTimer?.cancel();
    await _positionSub?.cancel();
    super.dispose();
  }
}
