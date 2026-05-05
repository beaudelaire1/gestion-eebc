import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../config/app_config.dart';
import '../models/user.dart';
import '../services/auth_service.dart';
import '../services/notification_service.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final user = auth.currentUser;

    if (!auth.isAuthenticated || user == null) {
      return Scaffold(
        backgroundColor: Colors.white,
        body: SafeArea(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  gradient: AppConfig.primaryGradient,
                  borderRadius: BorderRadius.circular(22),
                  boxShadow: [
                    BoxShadow(
                      color: AppConfig.primaryColor.withValues(alpha: 0.25),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: const Icon(Icons.person_outline, color: Colors.white, size: 40),
              ),
              const SizedBox(height: 24),
              Text(
                'Accédez à votre profil',
                style: GoogleFonts.poppins(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  color: AppConfig.darkBlack,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Connectez-vous pour voir vos informations',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  color: AppConfig.gray500,
                ),
              ),
              const SizedBox(height: 32),
              Container(
                height: 48,
                decoration: BoxDecoration(
                  gradient: AppConfig.loginButtonGradient,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: AppConfig.primaryColor.withValues(alpha: 0.25),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: ElevatedButton.icon(
                  onPressed: () => context.go('/login'),
                  icon: const Icon(Icons.login, color: Colors.white),
                  label: Text(
                    'Se connecter',
                    style: GoogleFonts.poppins(
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    shadowColor: Colors.transparent,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // ─── Profile header ───
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            backgroundColor: AppConfig.primaryColor,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(gradient: AppConfig.primaryGradient),
                child: SafeArea(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const SizedBox(height: 16),
                      Container(
                        width: 72,
                        height: 72,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.4),
                            width: 2,
                          ),
                        ),
                        child: Center(
                          child: Text(
                            '${user.firstName.isNotEmpty ? user.firstName[0] : ''}${user.lastName.isNotEmpty ? user.lastName[0] : ''}'
                                .toUpperCase(),
                            style: GoogleFonts.poppins(
                              fontSize: 26,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        user.fullName,
                        style: GoogleFonts.poppins(
                          fontSize: 20,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        user.email,
                        style: GoogleFonts.poppins(
                          fontSize: 13,
                          color: Colors.white.withValues(alpha: 0.75),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ─── Menu items ───
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _buildProfileMenuItem(
                    context,
                    icon: Icons.lock_outline,
                    iconColor: AppConfig.warningColor,
                    title: 'Changer le mot de passe',
                    subtitle: 'Modifier votre mot de passe',
                    onTap: () => context.push('/change-password'),
                  ),
                  const SizedBox(height: 8),
                  _buildProfileMenuItem(
                    context,
                    icon: Icons.settings_outlined,
                    iconColor: AppConfig.gray500,
                    title: 'Paramètres',
                    subtitle: 'Thème, notifications',
                    onTap: () => context.push('/settings'),
                  ),
                  const SizedBox(height: 8),
                  _buildProfileMenuItem(
                    context,
                    icon: Icons.volunteer_activism_outlined,
                    iconColor: AppConfig.secondaryColor,
                    title: 'Mes dons',
                    subtitle: 'Historique de vos dons',
                    onTap: () => context.push('/donations'),
                  ),
                  if (_isDriverOrAdmin(user))
                    const SizedBox(height: 8),
                  if (_isDriverOrAdmin(user))
                    _buildProfileMenuItem(
                      context,
                      icon: Icons.directions_car_rounded,
                      iconColor: Colors.teal,
                      title: 'Mes courses',
                      subtitle: 'Suivi GPS chauffeur',
                      onTap: () => context.push('/driver-tracking'),
                    ),
                  const SizedBox(height: 24),

                  // Logout button
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () async {
                        final notificationService =
                            context.read<NotificationService>();
                        final authService = context.read<AuthService>();
                        await notificationService.unregisterCurrentToken();
                        await authService.logout();
                        if (!context.mounted) return;
                        context.go('/login');
                      },
                      icon: const Icon(Icons.logout, color: AppConfig.dangerColor),
                      label: Text(
                        'Se déconnecter',
                        style: GoogleFonts.poppins(
                          color: AppConfig.dangerColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppConfig.dangerColor),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 24),
                  Text(
                    'Version ${AppConfig.appVersion}',
                    style: GoogleFonts.poppins(
                      fontSize: 12,
                      color: AppConfig.gray400,
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  bool _isDriverOrAdmin(User user) {
    final role = user.role?.toLowerCase() ?? '';
    return role.contains('chauffeur') ||
        role.contains('admin') ||
        role.contains('secrétariat') ||
        role.contains('secretariat');
  }

  Widget _buildProfileMenuItem(
    BuildContext context, {
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardTheme.color ?? Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Theme.of(context).dividerColor.withValues(alpha: 0.15),
        ),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: iconColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: iconColor, size: 22),
        ),
        title: Text(
          title,
          style: GoogleFonts.poppins(fontSize: 15, fontWeight: FontWeight.w500),
        ),
        subtitle: Text(
          subtitle,
          style: GoogleFonts.poppins(fontSize: 12, color: AppConfig.gray500),
        ),
        trailing: Icon(Icons.chevron_right, color: AppConfig.gray400, size: 22),
      ),
    );
  }
}
