import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../models/announcement.dart';
import '../models/event.dart';
import '../models/member.dart';
import '../models/worship_service.dart';
import '../models/public_news.dart';
import '../screens/announcement_detail_screen.dart';
import '../screens/app_shell_screen.dart';
import '../screens/change_password_screen.dart';
import '../screens/donations_screen.dart';
import '../screens/event_detail_screen.dart';
import '../screens/member_detail_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/worship_detail_screen.dart';
import '../screens/public_sites_screen.dart';
import '../screens/public_map_screen.dart';
import '../screens/public_news_screen.dart';
import '../screens/public_news_detail_screen.dart';
import '../screens/driver_tracking_screen.dart';
import '../screens/public_contact_screen.dart';
import '../screens/public_interest_screen.dart';
import '../services/auth_service.dart';
import '../screens/login_screen.dart';
import '../screens/home_screen.dart';
import '../screens/members_screen.dart';
import '../screens/events_screen.dart';
import '../screens/worship_screen.dart';
import '../screens/announcements_screen.dart';
import '../screens/bible_club_screen.dart';
import '../screens/profile_screen.dart';

class AppRouter {
  static final _rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');

  static final GoRouter router = GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/home',
    debugLogDiagnostics: false,
    redirect: (context, state) {
      final authService = context.read<AuthService>();
      final isLoggedIn = authService.isAuthenticated;
      final location = state.matchedLocation;

      // Pages accessibles à tous sans connexion
      const publicPaths = {
        '/login',
        '/home',
        '/events',
        '/events/detail',
        '/worship',
        '/worship/detail',
        '/announcements',
        '/announcements/detail',
        '/public/sites',
        '/public/map',
        '/public/news',
        '/public/news/detail',
        '/public/contact',
        '/public/interest',
      };

      // Pages qui nécessitent une connexion
      if (!isLoggedIn && !publicPaths.contains(location)) {
        return '/login';
      }

      // Si déjà connecté, ne pas montrer le login
      if (isLoggedIn && location == '/login') {
        return '/home';
      }

      // Forcer le changement de mot de passe
      if (isLoggedIn && authService.currentUser?.mustChangePassword == true && location != '/change-password') {
        return '/change-password';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => AppShellScreen(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/home', name: 'home', builder: (context, state) => const HomeScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/members', name: 'members', builder: (context, state) => const MembersScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/events', name: 'events', builder: (context, state) => const EventsScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/worship', name: 'worship', builder: (context, state) => const WorshipScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', name: 'profile', builder: (context, state) => const ProfileScreen()),
          ]),
        ],
      ),
      GoRoute(
        path: '/announcements',
        name: 'announcements',
        builder: (context, state) => const AnnouncementsScreen(),
      ),
      GoRoute(
        path: '/bible-club',
        name: 'bible-club',
        builder: (context, state) => const BibleClubScreen(),
      ),
      GoRoute(
        path: '/donations',
        name: 'donations',
        builder: (context, state) => const DonationsScreen(),
      ),
      GoRoute(
        path: '/settings',
        name: 'settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/change-password',
        name: 'change-password',
        builder: (context, state) => const ChangePasswordScreen(),
      ),
      GoRoute(
        path: '/members/detail',
        name: 'member-detail',
        builder: (context, state) => MemberDetailScreen(member: state.extra as Member),
      ),
      GoRoute(
        path: '/events/detail',
        name: 'event-detail',
        builder: (context, state) => EventDetailScreen(event: state.extra as EventItem),
      ),
      GoRoute(
        path: '/worship/detail',
        name: 'worship-detail',
        builder: (context, state) => WorshipDetailScreen(service: state.extra as WorshipService),
      ),
      GoRoute(
        path: '/announcements/detail',
        name: 'announcement-detail',
        builder: (context, state) => AnnouncementDetailScreen(announcement: state.extra as Announcement),
      ),
      GoRoute(
        path: '/public/sites',
        name: 'public-sites',
        builder: (context, state) => const PublicSitesScreen(),
      ),
      GoRoute(
        path: '/public/map',
        name: 'public-map',
        builder: (context, state) => const PublicMapScreen(),
      ),
      GoRoute(
        path: '/public/news',
        name: 'public-news',
        builder: (context, state) => const PublicNewsScreen(),
      ),
      GoRoute(
        path: '/public/news/detail',
        name: 'public-news-detail',
        builder: (context, state) => PublicNewsDetailScreen(item: state.extra as PublicNewsItem),
      ),
      GoRoute(
        path: '/public/contact',
        name: 'public-contact',
        builder: (context, state) => const PublicContactScreen(),
      ),
      GoRoute(
        path: '/public/interest',
        name: 'public-interest',
        builder: (context, state) => const PublicInterestScreen(),
      ),
      GoRoute(
        path: '/driver-tracking',
        name: 'driver-tracking',
        builder: (context, state) => const DriverTrackingScreen(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Page non trouvée: ${state.matchedLocation}'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => context.go('/home'),
              child: const Text('Retour à l\'accueil'),
            ),
          ],
        ),
      ),
    ),
  );
}
