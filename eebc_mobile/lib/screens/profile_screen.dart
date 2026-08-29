import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Profil')),
    body: Consumer<AuthService>(builder: (ctx, auth, _) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text('${auth.fullName ?? "Utilisateur"}'),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () async => await auth.logout(),
            child: const Text('Déconnexion'),
          ),
        ],
      ),
    )),
  );
}
