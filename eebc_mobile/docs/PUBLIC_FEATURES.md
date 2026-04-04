# Public Features Documentation

## Overview

The EEBC mobile app includes a comprehensive public section accessible without authentication, mirroring the website's public pages. This section provides:

- **Nos Églises** (Church Directory) - Display all church locations with contact info and service times
- **Actualités** (News) - Browse published articles with images and excerpts
- **Carte Interactive** (Interactive Map) - View church locations on Google Maps
- **Contact** - Submit contact forms with rate limiting protection
- **Je suis intéressé(e)** (Interest Form) - Visitor registration for church interest

## Architecture

### Backend API (`apps/api/`)

Public endpoints are fully documented in [API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md).

**Rate Limiting**: All public forms implement IP-based rate limiting (3 requests per 10 minutes) via `PublicRateLimitMixin`.

**Endpoints**:
- `GET /api/v1/public/sites/` - Church directory
- `GET /api/v1/public/news/` - News articles  
- `GET /api/v1/public/events/` - Public events
- `GET /api/v1/public/worship-schedules/` - Service times
- `GET /api/v1/public/settings/` - Site configuration
- `GET /api/v1/public/meta/` - Form choices
- `POST /api/v1/public/contact/` - Contact form submission
- `POST /api/v1/public/interest/` - Visitor registration

### Mobile Architecture

#### Data Models (`lib/models/public_*.dart`)

```
PublicSiteItem
├── id: int
├── name: String
├── address: String
├── city: String
├── phone: String
├── email: String
├── latitude: double
├── longitude: double
├── worshipSchedule: List<PublicWorshipSchedule>
└── isMainSite: bool

PublicNewsItem
├── id: int
├── title: String
├── slug: String
├── excerpt: String
├── content: String?
├── category: String
├── author: String
├── publishDate: DateTime
├── isFeatured: bool
└── imageUrl: String?

PublicWorshipSchedule
├── id: int
├── site: PublicSiteItem
├── name: String
├── dayOfWeek: int
├── dayOfWeekLabel: String
├── startTime: String
├── endTime: String
└── description: String?

PublicMeta
├── contactSubjects: List<PublicChoice>
└── visitorInterests: List<PublicChoice>
```

#### State Management (Providers)

All providers implement offline-first caching with 10-minute validity window:

```dart
// Typical provider pattern
final provider = context.watch<PublicSitesProvider>();

// Check state
if (provider.isLoading) {
  return LoadingIndicator();
} else if (provider.error != null) {
  return ErrorState(onRetry: () => provider.fetchSites());
} else if (provider.sites.isEmpty) {
  return EmptyState();
} else {
  return ListView(
    children: provider.sites.map((site) => SiteCard(site)).toList(),
  );
}

// Offline indicator
if (provider.isOffline) {
  return OfflineNotice();
}
```

**Providers**:
- `PublicSitesProvider` - Church directory with address and contact
- `PublicNewsProvider` - Article list with lazy-loading for details
- `PublicSchedulesProvider` - Worship schedule list
- `PublicSettingsProvider` - Global site configuration

#### Services

**LocalCacheService** (`services/local_cache_service.dart`)
- Stores data in SharedPreferences with timestamp
- Provides automatic staleness detection (10-minute window)
- Fallback to cached data during network failures

```dart
final cacheService = context.read<LocalCacheService>();

// Write to cache
await cacheService.write('public_sites', sitesList);

// Read with staleness check
final cached = cacheService.read('public_sites');
if (cached.isFresh) {
  // Use fresh data
} else if (cached.data != null) {
  // Use stale data but mark as offline
}
```

**PublicFormsService** (`services/public_forms_service.dart`)
- Contact form submission with validation
- Visitor registration form
- Honeypot field protection against bots

```dart
final formsService = context.read<PublicFormsService>();

// Fetch form choices
final meta = await formsService.fetchMeta();

// Submit contact form
try {
  await formsService.submitContact(ContactData(...));
} on ApiException catch (e) {
  if (e.statusCode == 429) {
    // Rate limit exceeded - show user message
  }
}
```

### UI Components

#### Screens

**PublicSitesScreen** (`screens/public_sites_screen.dart`)
- Displays church directory with cards
- Each card shows name, address, service times
- Action buttons: call, email, open Google Maps
- Offline notice if cached data is stale

**PublicMapScreen** (`screens/public_map_screen.dart`)
- Shows only churches with GPS coordinates
- Tap to open Google Maps with location
- Filters from PublicSitesProvider

**PublicNewsScreen** (`screens/public_news_screen.dart`)
- News list with featured images
- Excerpt (max 3 lines) for each article
- Tap to navigate to detail screen
- Empty state if no articles

**PublicNewsDetailScreen** (`screens/public_news_detail_screen.dart`)
- Full article view
- Lazy-loads content if not in list response
- Displays image, author, publication date
- Cached under `public_news_detail_{slug}`

**PublicContactScreen** (`screens/public_contact_screen.dart`)
- Contact form with fields: name, email, phone, subject, site, message
- Required fields: name, email, subject, message
- Subject dropdown populated from `/public/meta/`
- Honeypot field automatically hidden
- Error banner for validation/submission errors

**PublicInterestScreen** (`screens/public_interest_screen.dart`)
- Visitor registration form
- Fields: first name, last name, email, phone, city, interest, preferred site, message
- Interest dropdown populated from `/public/meta/`
- Similar structure and validation as contact form

#### Reusable Components

**EmptyState** (`widgets/common/empty_state.dart`)
- Centered icon + title + message
- Optional action button for retry or navigation
- Used by all list screens when zero items

**OfflineNotice** (`widgets/common/offline_notice.dart`)
- Yellow/orange banner with WiFi-off icon
- Message: "Mode hors ligne actif. Donnees en cache."
- Shows when displaying stale/cached data

## Routing

Public routes are registered in [lib/config/routes.dart](../lib/config/routes.dart):

```dart
// Public routes require no authentication
const publicPaths = {
  '/public/sites',
  '/public/map',
  '/public/news',
  '/public/news/detail',
  '/public/contact',
  '/public/interest',
};

// Route definitions
GoRoute(path: '/public/sites', builder: (context, state) => PublicSitesScreen()),
GoRoute(path: '/public/news', builder: (context, state) => PublicNewsScreen()),
GoRoute(path: '/public/news/detail', builder: (context, state) => 
  PublicNewsDetailScreen(item: state.extra as PublicNewsItem)),
// ... etc
```

## Usage Examples

### Display Church Directory

```dart
final sitesProvider = context.watch<PublicSitesProvider>();

// Trigger fetch on init
context.read<PublicSitesProvider>().fetchSites();

// Use provider data
if (sitesProvider.isLoading) {
  return LoadingSpinner();
} else if (sitesProvider.error != null) {
  return ErrorBanner(
    message: sitesProvider.error!,
    onRetry: () => context.read<PublicSitesProvider>().fetchSites(),
  );
} else {
  return Column(
    children: [
      if (sitesProvider.isOffline) OfflineNotice(),
      if (sitesProvider.sites.isEmpty)
        EmptyState(title: 'Aucune église', message: 'Aucune église trouvée'),
      ListView.builder(
        itemCount: sitesProvider.sites.length,
        itemBuilder: (context, index) {
          final site = sitesProvider.sites[index];
          return SiteCard(
            site: site,
            onCall: () => launchUrl(Uri(scheme: 'tel', path: site.phone)),
            onEmail: () => launchUrl(Uri(scheme: 'mailto', path: site.email)),
            onMap: () => launchUrl(Uri.parse(
              'https://maps.google.com/maps/search/?api=1&query=${site.latitude},${site.longitude}'
            )),
          );
        },
      ),
    ],
  );
}
```

### Submit Contact Form

```dart
final formsService = context.read<PublicFormsService>();

// Load meta (subjects/interests)
final meta = await formsService.fetchMeta();

// Submit form
try {
  await formsService.submitContact(
    name: 'Jean Dupont',
    email: 'jean@example.com',
    phone: '+33123456789',
    subject: 'info',
    siteId: 1,
    message: 'Bonjour, j\'aimerais...',
  );
  
  // Success - clear form, show confirmation
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Message envoyé avec succès')),
  );
} on ApiException catch (e) {
  if (e.statusCode == 429) {
    // Show rate limit message
    showErrorBanner(context, 'Trop de tentatives. Réessayez plus tard.');
  } else {
    // Show other errors
    showErrorBanner(context, e.message);
  }
}
```

### Offline Caching

Public data is automatically cached for 10 minutes:

```dart
// First load (from network, then cached)
final sites = await provider.fetchSites();

// Within 10 minutes - isFresh = true
final cached = cacheService.read('public_sites');
if (cached.isFresh && cached.data != null) {
  // Use fresh cached data
}

// After 10 minutes - isFresh = false
// If network fails, provider shows cached data with isOffline = true
```

## Rate Limiting

Public forms are protected with server-side rate limiting:

**Limits**:
- 3 requests per 10-minute window per IP address
- Applies to `/public/contact/` and `/public/interest/` endpoints

**Client Handling**:
```dart
try {
  await formsService.submitContact(...);
} on ApiException catch (e) {
  if (e.statusCode == 429) {
    // Rate limit hit - show message to user
    showSnackBar(context, 'Trop de tentatives. Réessayez dans 10 minutes.');
  }
}
```

## Testing

### Unit Tests

Run provider tests:
```bash
flutter test test/unit/providers/public_*.dart
```

### Integration Tests

Run full public feature tests:
```bash
flutter test test/public_features_integration_test.dart
```

### API Tests

Run backend API tests:
```bash
python manage.py test apps.api.tests.PublicApiTests
```

## Performance Considerations

1. **Image Loading**: 
   - Load images lazily in lists using `Image.network` with `fit: BoxFit.cover`
   - Cache with HTTP `Cache-Control` headers
   
2. **News Detail**:
   - Lazy-load full content only when user navigates to detail
   - Cache under individual keys: `public_news_detail_{slug}`

3. **Caching Strategy**:
   - 10-minute validity window balances freshness vs. network requests
   - Can be adjusted in `AppConfig.cacheValidity`

4. **Error Handling**:
   - All screens show specific error messages
   - Retry button on errors to refetch

## Security

1. **Honeypot Fields**: Contact and interest forms include honeypot field to prevent bot submissions
2. **Rate Limiting**: IP-based limiting on form endpoints
3. **CORS**: Public endpoints use `AllowAny` permissions
4. **Input Validation**: Email, required fields validated client-side and server-side

## Future Enhancements

- [ ] Add search/filter to church directory
- [ ] Add pagination to news list
- [ ] Add comments/reactions to articles
- [ ] Add push notifications for featured news
- [ ] Add sharing to social media
- [ ] Add translation to multiple languages using `easy_localization`
- [ ] Add image optimization/resizing
- [ ] Implement real offline-first synchronization queue

## Related Files

- Backend: [apps/api/views.py](../../apps/api/views.py)
- Backend: [apps/api/serializers.py](../../apps/api/serializers.py)
- Backend: [apps/api/tests.py](../../apps/api/tests.py)
- Backend: [docs/API_DOCUMENTATION.md](../../docs/API_DOCUMENTATION.md)
- Mobile: [lib/config/routes.dart](../lib/config/routes.dart)
- Mobile: [lib/main.dart](../lib/main.dart)
