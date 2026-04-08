# 🚀 GUIDE RAPIDE : Vérifier le déploiement Render

## ✅ CE QUI A ÉTÉ CORRIGÉ

### 3 commits pushés sur `develop`

1. **417f64d** - Correctif "Nouvelle Famille" (boucle infinie + UX)
2. **cee7463** - Config PORT dynamique (start.sh)
3. **3bee8f7** - PORT explicite + Gunicorn preload (**critique**)

---

## 🔍 ACTIONS À FAIRE MAINTENANT

### 1. Surveiller les logs Render (5 min)

**URL** : https://dashboard.render.com → `gestion-eebc` → **Logs**

**Ce que vous devez voir** :
```bash
=== Build ===
[OK] Installing dependencies...
[OK] Collecting static files...
[OK] Running migrations...
[OK] ✓ WSGI app loaded OK
[OK] Rendre les scripts exécutables

=== Démarrage ===
=== Configuration Gunicorn ===
PORT: 10000
WORKERS: 1
PYTHON VERSION: Python 3.x
DJANGO SETTINGS: gestion_eebc.settings.prod

[INFO] Starting gunicorn 25.1.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: gthread
[INFO] Booting worker with pid: XX

==> Your service is live 🎉
```

**✅ SIGNES DE SUCCÈS** :
- ✅ `PORT: 10000` affiché
- ✅ `Booting worker with pid: XX` présent
- ✅ `Your service is live 🎉`
- ✅ **PAS de** "New primary port detected"
- ✅ **PAS de** "No open HTTP ports detected"

---

### 2. Tester le service (1 min)

**URL** : https://eglise-ebc.org/app/

**Actions** :
1. ✅ Page d'accueil charge (< 3s)
2. ✅ Login fonctionne
3. ✅ Navigation fluide
4. ✅ **Test critique** : Aller sur **Nouvelle Famille** → Sélectionner un membre
   - Dropdown s'ouvre rapidement ✓
   - Photos/infos visibles ✓
   - Auto-remplissage fonctionne ✓
   - **PAS de boucle infinie** ✓

---

### 3. Si problème persiste

#### Option A : Manual Deploy (forcer redéploiement)

1. Dashboard Render → `gestion-eebc`
2. **Manual Deploy** (bouton en haut à droite)
3. Sélectionner : `Branch: develop` + `Clear build cache: YES`
4. **Deploy**
5. Attendre 3-5 min

#### Option B : Vérifier variables d'environnement

Dashboard → `gestion-eebc` → **Environment**

**Variables critiques** :
```
PORT = 10000                              ← DOIT être présent
DJANGO_SETTINGS_MODULE = gestion_eebc.settings.prod
DATABASE_URL = postgresql://...          ← Doit pointer vers eebc-db
ALLOWED_HOSTS = .onrender.com
SECRET_KEY = (généré automatiquement)
```

#### Option C : Check service health

```bash
curl https://eglise-ebc.org/healthz/ping/
# Doit retourner : OK
```

Si erreur 503 :
```bash
# Vérifier dans logs Render
grep "ERROR" /var/log/...
grep "workers" /var/log/...
```

---

## 📊 RÉSUMÉ TECHNIQUE

| Aspect | Avant | Après |
|--------|-------|-------|
| **Port config** | Hardcodé inline | Explicite envVar |
| **Gunicorn** | Workers fail après restart | --preload + graceful |
| **Auto-deploy** | Manuel | Automatique |
| **Nouvelle Famille** | Boucle infinie | Stable + UX |
| **Logs** | Silencieux | Verbeux (debug) |

---

## 🎯 CHECKLIST FINALE

- [ ] Logs Render montrent "Booting worker"
- [ ] "Your service is live 🎉" affiché
- [ ] Site https://eglise-ebc.org accessible
- [ ] Page "Nouvelle Famille" fonctionne sans boucle
- [ ] Aucun restart automatique Render
- [ ] Healthcheck `/healthz/ping/` retourne OK

**Si tous les points sont ✅** → **Déploiement réussi !** 🎉

---

## 📞 EN CAS DE PROBLÈME

**Si service down après 10 min** :

1. Screenshot des logs Render
2. Vérifier message d'erreur exact
3. Options :
   - Rollback vers commit précédent stable
   - Clear build cache + redeploy
   - Vérifier DATABASE_URL connectivity

**Contact** : Logs Render → Share → Envoyer URL des logs

---

## 🚀 PROCHAINES ÉTAPES

Une fois service stable :

1. ✅ Tester intensivement page "Nouvelle Famille"
2. ✅ Vérifier autres pages critiques (membres, dashboard)
3. ✅ Monitorer les erreurs Django (si Sentry configuré)
4. 📝 Documenter les changements pour l'équipe

---

**Temps estimé de déploiement** : 3-5 minutes  
**Temps de stabilisation** : < 2 minutes après "live"

**Score de confiance** : 9.5/10 ⭐

---

*Généré automatiquement - Correctif Render du 18 février 2026*
