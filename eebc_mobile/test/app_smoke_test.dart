import 'package:eebc_mobile/providers/announcements_provider.dart';
import 'package:eebc_mobile/providers/events_provider.dart';
import 'package:eebc_mobile/providers/members_provider.dart';
import 'package:eebc_mobile/providers/theme_provider.dart';
import 'package:eebc_mobile/providers/worship_provider.dart';
import 'package:eebc_mobile/screens/events_screen.dart';
import 'package:eebc_mobile/screens/home_screen.dart';
import 'package:eebc_mobile/screens/login_screen.dart';
import 'package:eebc_mobile/services/api_service.dart';
import 'package:eebc_mobile/services/auth_service.dart';
import 'package:eebc_mobile/services/local_cache_service.dart';
import 'package:eebc_mobile/services/notification_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

class FakeApiService extends ApiService {
  @override
  Future<Map<String, dynamic>> get(String endpoint, {Map<String, dynamic>? queryParameters}) async {
    if (endpoint == '/events/') {
      return {
        'results': [
          {
            'id': 1,
            'title': 'Culte du dimanche',
            'start_date': '2026-02-22',
            'location': 'Cabassou',
          }
        ],
      };
    }

    if (endpoint == '/announcements/') {
      return {
        'results': [
          {
            'id': 1,
            'title': 'Annonce test',
            'content': 'Contenu',
            'is_pinned': false,
          }
        ],
      };
    }

    if (endpoint == '/members/') {
      return {'results': []};
    }

    return {'results': []};
  }

  @override
  Future<Map<String, dynamic>> post(String endpoint, Map<String, dynamic> data) async {
    return {'data': {'ok': true}};
  }

  @override
  Future<Map<String, dynamic>> put(String endpoint, Map<String, dynamic> data) async {
    return {'data': {'ok': true}};
  }

  @override
  Future<void> delete(String endpoint) async {}
}

Widget _wrapWithProviders(Widget child) {
  final api = FakeApiService();
  final auth = AuthService(api);
  final cacheService = LocalCacheService();

  return MultiProvider(
    providers: [
      Provider<ApiService>.value(value: api),
      Provider<LocalCacheService>.value(value: cacheService),
      Provider<NotificationService>.value(value: NotificationService(api)),
      ChangeNotifierProvider<AuthService>.value(value: auth),
      ChangeNotifierProvider(create: (_) => ThemeProvider()),
      ChangeNotifierProvider(create: (_) => MembersProvider(api)),
      ChangeNotifierProvider(create: (_) => EventsProvider(api, cacheService)),
      ChangeNotifierProvider(create: (_) => WorshipProvider(api, cacheService)),
      ChangeNotifierProvider(create: (_) => AnnouncementsProvider(api, cacheService)),
    ],
    child: MaterialApp(home: child),
  );
}

void main() {
  setUpAll(() async {
    await initializeDateFormatting('fr_FR', null);
  });

  testWidgets('LoginScreen renders form fields', (tester) async {
    await tester.pumpWidget(_wrapWithProviders(const LoginScreen()));
    expect(find.text('Connexion'), findsOneWidget);
    expect(find.text('Identifiant'), findsOneWidget);
    expect(find.text('Mot de passe'), findsOneWidget);
  });

  testWidgets('HomeScreen renders dashboard', (tester) async {
    await tester.pumpWidget(_wrapWithProviders(const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Bienvenue'), findsOneWidget);
    expect(find.text('Prochains événements'), findsOneWidget);
  });

  testWidgets('EventsScreen displays fetched event', (tester) async {
    await tester.pumpWidget(_wrapWithProviders(const EventsScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Culte du dimanche'), findsOneWidget);
    expect(find.textContaining('Cabassou'), findsOneWidget);
  });
}
