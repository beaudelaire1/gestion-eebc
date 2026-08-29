import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/transport_request.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../services/transport_tracking_service.dart';
import '../widgets/common/error_state.dart';
import '../widgets/common/loading_indicator.dart';

/// Écran principal du chauffeur : liste ses courses et gère le suivi GPS live.
class DriverTrackingScreen extends StatefulWidget {
  const DriverTrackingScreen({super.key});

  @override
  State<DriverTrackingScreen> createState() => _DriverTrackingScreenState();
}

class _DriverTrackingScreenState extends State<DriverTrackingScreen> {
  late TransportTrackingService _trackingService;

  @override
  void initState() {
    super.initState();
    _trackingService = TransportTrackingService(context.read<ApiService>());
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _trackingService.fetchMyRequests();
    });
  }

  @override
  void dispose() {
    _trackingService.dispose();
    super.dispose();
  }

  Future<void> _toggleTracking(TransportRequest req) async {
    if (_trackingService.isTracking && _trackingService.activeRequestId == req.id) {
      await _trackingService.stopTracking();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Suivi GPS arrêté')),
        );
      }
    } else {
      final started = await _trackingService.startTracking(req.id);
      if (!mounted) return;
      if (started) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Suivi GPS démarré pour "${req.eventName}"')),
        );
      } else if (_trackingService.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_trackingService.error!),
            backgroundColor: Colors.red,
          ),
        );
        _trackingService.clearError();
      }
    }
    await _trackingService.fetchMyRequests();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: _trackingService,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mes courses'),
          actions: [
            Consumer<TransportTrackingService>(
              builder: (_, svc, __) => IconButton(
                icon: svc.loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh),
                onPressed: svc.loading ? null : svc.fetchMyRequests,
                tooltip: 'Rafraîchir',
              ),
            ),
          ],
        ),
        body: Consumer<TransportTrackingService>(
          builder: (context, svc, _) {
            if (svc.loading && svc.myRequests.isEmpty) {
              return const LoadingIndicator();
            }

            if (svc.error != null && svc.myRequests.isEmpty) {
              return ErrorState(
                message: svc.error!,
                onRetry: svc.fetchMyRequests,
              );
            }

            if (svc.myRequests.isEmpty) {
              return const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.directions_car_outlined, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text(
                        'Aucune course assignée',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Vos courses confirmées apparaîtront ici.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              );
            }

            return Column(
              children: [
                // Bandeau de statut tracking actif
                if (svc.isTracking)
                  _ActiveTrackingBanner(service: svc),

                // Liste des courses
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: svc.fetchMyRequests,
                    child: ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: svc.myRequests.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final req = svc.myRequests[index];
                        final isActive = svc.isTracking && svc.activeRequestId == req.id;
                        return _RequestCard(
                          request: req,
                          isTrackingActive: isActive,
                          onToggle: () => _toggleTracking(req),
                          trackingDisabled: svc.isTracking && !isActive,
                        );
                      },
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

// ── Bandeau tracking actif ────────────────────────────────────────────────────

class _ActiveTrackingBanner extends StatelessWidget {
  final TransportTrackingService service;

  const _ActiveTrackingBanner({required this.service});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final speed = service.lastSpeedKmh;
    final accuracy = service.lastAccuracy;

    return Container(
      width: double.infinity,
      color: colorScheme.primaryContainer,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          const Icon(Icons.gps_fixed, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Suivi en cours',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.onPrimaryContainer,
                  ),
                ),
                if (speed != null || accuracy != null)
                  Text(
                    [
                      if (speed != null) '${speed.toStringAsFixed(0)} km/h',
                      if (accuracy != null)
                        'précision ±${accuracy.toStringAsFixed(0)} m',
                    ].join('  ·  '),
                    style: TextStyle(
                      fontSize: 12,
                      color: colorScheme.onPrimaryContainer.withValues(alpha: 0.8),
                    ),
                  ),
              ],
            ),
          ),
          // Indicateur pulse
          _PulsingDot(color: colorScheme.primary),
        ],
      ),
    );
  }
}

class _PulsingDot extends StatefulWidget {
  final Color color;
  const _PulsingDot({required this.color});

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.4, end: 1.0).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _animation,
      child: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: widget.color,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}

// ── Carte de course ───────────────────────────────────────────────────────────

class _RequestCard extends StatelessWidget {
  final TransportRequest request;
  final bool isTrackingActive;
  final VoidCallback onToggle;
  final bool trackingDisabled;

  const _RequestCard({
    required this.request,
    required this.isTrackingActive,
    required this.onToggle,
    required this.trackingDisabled,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Card(
      elevation: isTrackingActive ? 4 : 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isTrackingActive
            ? BorderSide(color: colorScheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // En-tête : nom de l'événement + statut
            Row(
              children: [
                const Icon(Icons.event_rounded, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    request.eventName.isNotEmpty ? request.eventName : 'Course',
                    style: textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
                _StatusChip(status: request.status),
              ],
            ),
            const SizedBox(height: 12),

            // Date + heure
            _InfoRow(
              icon: Icons.schedule_rounded,
              text:
                  '${_formatDate(request.eventDate)}  ·  ${request.eventTime}',
            ),
            const SizedBox(height: 6),

            // Adresse de prise en charge
            _InfoRow(
              icon: Icons.location_on_rounded,
              text: request.pickupAddress,
            ),
            const SizedBox(height: 6),

            // Passagers
            _InfoRow(
              icon: Icons.people_alt_rounded,
              text: '${request.passengersCount} passager(s)',
            ),
            const SizedBox(height: 6),

            // Contact demandeur
            _InfoRow(
              icon: Icons.person_rounded,
              text: request.requesterName,
            ),
            if (request.requesterPhone.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: _InfoRow(
                  icon: Icons.phone_rounded,
                  text: request.requesterPhone,
                ),
              ),

            const SizedBox(height: 16),
            const Divider(height: 1),
            const SizedBox(height: 12),

            // Bouton tracking
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: trackingDisabled ? null : onToggle,
                icon: Icon(
                  isTrackingActive
                      ? Icons.stop_circle_outlined
                      : Icons.gps_fixed_rounded,
                ),
                label: Text(
                  isTrackingActive
                      ? 'Arrêter le suivi GPS'
                      : 'Démarrer le suivi GPS',
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isTrackingActive
                      ? colorScheme.errorContainer
                      : colorScheme.primaryContainer,
                  foregroundColor: isTrackingActive
                      ? colorScheme.onErrorContainer
                      : colorScheme.onPrimaryContainer,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    const months = [
      'jan', 'fév', 'mar', 'avr', 'mai', 'jun',
      'jul', 'aoû', 'sep', 'oct', 'nov', 'déc',
    ];
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Expanded(
          child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
        ),
      ],
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    String label;
    switch (status) {
      case 'confirmed':
        bg = Colors.green.shade100;
        fg = Colors.green.shade800;
        label = 'Confirmé';
        break;
      case 'pending':
        bg = Colors.orange.shade100;
        fg = Colors.orange.shade800;
        label = 'En attente';
        break;
      default:
        bg = Colors.grey.shade200;
        fg = Colors.grey.shade700;
        label = status;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: fg),
      ),
    );
  }
}
