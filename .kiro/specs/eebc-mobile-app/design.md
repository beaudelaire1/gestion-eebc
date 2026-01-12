# Design Document: EEBC Mobile App

## Overview

Application mobile cross-platform pour l'Église Évangélique Baptiste de Cabassou (EEBC) permettant aux membres d'accéder aux fonctionnalités de gestion depuis leur smartphone. L'application utilise React Native avec Expo pour le développement cross-platform et se connecte au backend Django existant via une API REST sécurisée par JWT.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EEBC Mobile App                          │
│                     (React Native + Expo)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Screens   │  │ Components  │  │   Hooks     │             │
│  │  - Login    │  │  - Header   │  │  - useAuth  │             │
│  │  - Dashboard│  │  - Card     │  │  - useApi   │             │
│  │  - Members  │  │  - List     │  │  - useCache │             │
│  │  - Events   │  │  - Form     │  │  - useNotif │             │
│  │  - Worship  │  │  - Modal    │  │             │             │
│  │  - Giving   │  │             │  │             │             │
│  │  - Profile  │  │             │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    State Management                      │   │
│  │                    (Zustand Store)                       │   │
│  │  - authStore (user, tokens, isAuthenticated)            │   │
│  │  - membersStore (list, search, cache)                   │   │
│  │  - eventsStore (calendar, registrations)                │   │
│  │  - worshipStore (services, assignments)                 │   │
│  │  - announcementsStore (list, unread count)              │   │
│  │  - offlineStore (queue, syncStatus)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Services Layer                        │   │
│  │  - ApiService (axios + interceptors)                    │   │
│  │  - AuthService (login, logout, refresh)                 │   │
│  │  - StorageService (SecureStore + AsyncStorage)          │   │
│  │  - NotificationService (Expo Notifications)             │   │
│  │  - SyncService (offline queue management)               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS / JWT
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Django REST API                             │
│                  (https://eglise-ebc.org/api/v1/)              │
├─────────────────────────────────────────────────────────────────┤
│  /auth/login/          POST   - Authenticate user              │
│  /auth/refresh/        POST   - Refresh JWT token              │
│  /auth/logout/         POST   - Invalidate token               │
│  /auth/password/       PUT    - Change password                │
│  /members/             GET    - List members                   │
│  /members/{id}/        GET    - Member detail                  │
│  /events/              GET    - List events                    │
│  /events/{id}/register POST   - Register for event             │
│  /worship/services/    GET    - List services                  │
│  /worship/confirm/     POST   - Confirm assignment             │
│  /announcements/       GET    - List announcements             │
│  /donations/           GET/POST - Donations                    │
│  /profile/             GET/PUT - User profile                  │
│  /notifications/register POST - Register device token          │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Navigation Structure

```typescript
// App Navigation (React Navigation)
type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
};

type AuthStackParamList = {
  Login: undefined;
  ChangePassword: { mustChange: boolean };
};

type MainTabParamList = {
  Dashboard: undefined;
  Members: undefined;
  Events: undefined;
  Worship: undefined;
  More: undefined;
};

type MoreStackParamList = {
  MoreMenu: undefined;
  Announcements: undefined;
  Giving: undefined;
  Profile: undefined;
  Settings: undefined;
};
```

### API Service Interface

```typescript
interface ApiService {
  // Configuration
  baseURL: string;
  timeout: number;
  
  // Methods
  get<T>(endpoint: string, params?: object): Promise<ApiResponse<T>>;
  post<T>(endpoint: string, data: object): Promise<ApiResponse<T>>;
  put<T>(endpoint: string, data: object): Promise<ApiResponse<T>>;
  delete(endpoint: string): Promise<ApiResponse<void>>;
  
  // Interceptors
  setAuthToken(token: string): void;
  clearAuthToken(): void;
  onTokenExpired(callback: () => Promise<string>): void;
}

interface ApiResponse<T> {
  data: T;
  status: number;
  success: boolean;
  error?: string;
}
```

### Auth Service Interface

```typescript
interface AuthService {
  login(username: string, password: string): Promise<AuthResult>;
  logout(): Promise<void>;
  refreshToken(): Promise<string>;
  changePassword(oldPassword: string, newPassword: string): Promise<void>;
  isAuthenticated(): Promise<boolean>;
  getCurrentUser(): Promise<User | null>;
  enableBiometric(): Promise<void>;
  authenticateWithBiometric(): Promise<AuthResult>;
}

interface AuthResult {
  success: boolean;
  user?: User;
  accessToken?: string;
  refreshToken?: string;
  mustChangePassword?: boolean;
  error?: string;
}

interface User {
  id: number;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  memberId?: number;
  permissions: string[];
}

type UserRole = 'admin' | 'pastor' | 'secretary' | 'leader' | 'member';
```

### Storage Service Interface

```typescript
interface StorageService {
  // Secure storage (for tokens)
  setSecure(key: string, value: string): Promise<void>;
  getSecure(key: string): Promise<string | null>;
  deleteSecure(key: string): Promise<void>;
  
  // Regular storage (for cache)
  set(key: string, value: any): Promise<void>;
  get<T>(key: string): Promise<T | null>;
  delete(key: string): Promise<void>;
  clear(): Promise<void>;
}
```

### Notification Service Interface

```typescript
interface NotificationService {
  requestPermission(): Promise<boolean>;
  registerDevice(userId: number): Promise<void>;
  unregisterDevice(): Promise<void>;
  getDeviceToken(): Promise<string | null>;
  
  // Local notifications
  scheduleLocalNotification(notification: LocalNotification): Promise<string>;
  cancelNotification(id: string): Promise<void>;
  
  // Handlers
  onNotificationReceived(handler: (notification: Notification) => void): void;
  onNotificationTapped(handler: (notification: Notification) => void): void;
}

interface LocalNotification {
  title: string;
  body: string;
  data?: object;
  trigger: { date: Date } | { seconds: number };
}
```

### Sync Service Interface

```typescript
interface SyncService {
  // Queue management
  queueAction(action: QueuedAction): Promise<void>;
  getQueuedActions(): Promise<QueuedAction[]>;
  clearQueue(): Promise<void>;
  
  // Sync operations
  syncAll(): Promise<SyncResult>;
  syncMembers(): Promise<void>;
  syncEvents(): Promise<void>;
  syncAnnouncements(): Promise<void>;
  
  // Status
  isOnline(): boolean;
  getLastSyncTime(): Promise<Date | null>;
  onConnectivityChange(handler: (isOnline: boolean) => void): void;
}

interface QueuedAction {
  id: string;
  type: 'event_register' | 'worship_confirm' | 'profile_update';
  endpoint: string;
  method: 'POST' | 'PUT' | 'DELETE';
  data: object;
  createdAt: Date;
  retryCount: number;
}

interface SyncResult {
  success: boolean;
  synced: number;
  failed: number;
  conflicts: SyncConflict[];
}
```

## Data Models

### Member Model

```typescript
interface Member {
  id: number;
  memberId: string;
  firstName: string;
  lastName: string;
  email?: string;
  phone?: string;
  whatsappNumber?: string;
  photo?: string;
  dateOfBirth?: string;
  gender: 'M' | 'F';
  maritalStatus: string;
  address?: string;
  city?: string;
  postalCode?: string;
  isBaptized: boolean;
  baptismDate?: string;
  status: 'active' | 'inactive' | 'visitor';
  family?: FamilyInfo;
  site: Site;
}

interface FamilyInfo {
  id: number;
  name: string;
  role: 'head' | 'spouse' | 'child' | 'other';
  members: FamilyMember[];
}

interface FamilyMember {
  id: number;
  firstName: string;
  lastName: string;
  relationship: string;
}
```

### Event Model

```typescript
interface Event {
  id: number;
  title: string;
  description: string;
  eventType: string;
  startDate: string;
  endDate: string;
  location?: string;
  isRecurring: boolean;
  maxParticipants?: number;
  currentParticipants: number;
  allowsRegistration: boolean;
  isUserRegistered: boolean;
  site: Site;
}

interface EventRegistration {
  id: number;
  eventId: number;
  memberId: number;
  status: 'registered' | 'cancelled' | 'attended';
  registeredAt: string;
}
```

### Worship Service Model

```typescript
interface WorshipService {
  id: number;
  date: string;
  serviceType: string;
  theme?: string;
  preacher?: string;
  status: 'planned' | 'confirmed' | 'completed';
  assignments: ServiceAssignment[];
  songs: Song[];
  site: Site;
}

interface ServiceAssignment {
  id: number;
  role: ServiceRole;
  member: MemberSummary;
  status: 'pending' | 'confirmed' | 'declined';
  isCurrentUser: boolean;
}

interface ServiceRole {
  id: number;
  name: string;
  category: 'music' | 'tech' | 'liturgy';
}

interface Song {
  id: number;
  title: string;
  author?: string;
  key?: string;
  order: number;
}
```

### Announcement Model

```typescript
interface Announcement {
  id: number;
  title: string;
  content: string;
  excerpt: string;
  imageUrl?: string;
  isPinned: boolean;
  publishedAt: string;
  expiresAt?: string;
  author: string;
  isRead: boolean;
  site: Site;
}
```

### Donation Model

```typescript
interface Donation {
  id: number;
  amount: number;
  currency: string;
  donationType: 'tithe' | 'offering' | 'special';
  fundName?: string;
  date: string;
  status: 'pending' | 'completed' | 'failed';
  receiptUrl?: string;
  isRecurring: boolean;
}

interface DonationRequest {
  amount: number;
  donationType: string;
  fundId?: number;
  isRecurring: boolean;
  recurringInterval?: 'weekly' | 'monthly';
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: JWT Token Lifecycle

*For any* authenticated user, storing a token then retrieving it SHALL return the same token value, and clearing tokens SHALL result in no tokens being retrievable.

**Validates: Requirements 1.3, 1.6**

### Property 2: Token Auto-Refresh

*For any* expired access token with a valid refresh token, the system SHALL automatically obtain a new valid access token without user intervention.

**Validates: Requirements 1.4**

### Property 3: Password Change Redirect

*For any* user with must_change_password flag set to true, authentication SHALL redirect to the password change screen before allowing access to main app.

**Validates: Requirements 1.5**

### Property 4: Account Lockout

*For any* sequence of 5 consecutive failed login attempts for the same user, the system SHALL display an account locked message.

**Validates: Requirements 1.8**

### Property 5: Role-Based Dashboard

*For any* authenticated user, the dashboard SHALL display only widgets appropriate for their role (admin sees all, member sees limited).

**Validates: Requirements 2.1, 2.6**

### Property 6: Event Date Filtering

*For any* date selection in the calendar, the displayed events SHALL only include events occurring on that specific date.

**Validates: Requirements 4.2**

### Property 7: Member Search Filtering

*For any* search query in the member directory, all returned results SHALL contain the search term in either name, phone, or email fields.

**Validates: Requirements 3.2**

### Property 8: Authorization Enforcement

*For any* member data request, the response SHALL only include fields the requesting user is authorized to view based on their role and privacy settings.

**Validates: Requirements 3.7**

### Property 9: Announcement Sorting

*For any* list of announcements, pinned announcements SHALL appear before non-pinned, and within each group, announcements SHALL be sorted by date descending.

**Validates: Requirements 6.2, 6.5**

### Property 10: Read Status Tracking

*For any* announcement viewed by a user, the announcement's isRead status SHALL be set to true and persist across sessions.

**Validates: Requirements 6.4**

### Property 11: Offline Data Availability

*For any* cached data (members, events, announcements), when the device is offline, the data SHALL remain accessible and display with an offline indicator.

**Validates: Requirements 9.1, 9.2, 3.8, 6.7**

### Property 12: Offline Action Queuing

*For any* action performed while offline (registration, confirmation), the action SHALL be queued and automatically executed when connectivity is restored.

**Validates: Requirements 9.3, 9.4**

### Property 13: Donation Persistence

*For any* successful donation transaction, the donation SHALL be recorded in the user's donation history and retrievable in subsequent sessions.

**Validates: Requirements 7.3, 7.4**

### Property 14: Profile Update Persistence

*For any* profile field update (photo, phone, email), the change SHALL be persisted to the backend and reflected in subsequent profile views.

**Validates: Requirements 10.2, 10.7**

### Property 15: Notification Deep Linking

*For any* push notification with associated content (announcement, event, assignment), tapping the notification SHALL navigate to the correct content screen.

**Validates: Requirements 8.5**

## Error Handling

### Network Errors

```typescript
enum NetworkError {
  NO_CONNECTION = 'NO_CONNECTION',
  TIMEOUT = 'TIMEOUT',
  SERVER_ERROR = 'SERVER_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
}

interface ErrorHandler {
  handleNetworkError(error: NetworkError): void;
  handleApiError(status: number, message: string): void;
  showRetryDialog(action: () => Promise<void>): void;
}
```

### Error Display Strategy

| Error Type | User Message | Action |
|------------|--------------|--------|
| NO_CONNECTION | "Pas de connexion internet" | Show offline mode, queue actions |
| TIMEOUT | "Le serveur met trop de temps à répondre" | Offer retry |
| SERVER_ERROR | "Une erreur est survenue" | Log error, offer retry |
| UNAUTHORIZED | "Session expirée" | Redirect to login |
| FORBIDDEN | "Accès non autorisé" | Show message, navigate back |
| PAYMENT_FAILED | "Le paiement a échoué" | Show details, offer retry |

## Testing Strategy

### Unit Tests

- Test all service methods in isolation
- Test Zustand store actions and selectors
- Test utility functions (date formatting, search filtering)
- Test form validation logic

### Property-Based Tests

Using fast-check library for React Native:

```typescript
import fc from 'fast-check';

// Property 7: Member Search Filtering
describe('Member Search', () => {
  it('should return only members matching search query', () => {
    fc.assert(
      fc.property(
        fc.array(memberArbitrary),
        fc.string({ minLength: 1 }),
        (members, query) => {
          const results = filterMembers(members, query);
          return results.every(m => 
            m.firstName.toLowerCase().includes(query.toLowerCase()) ||
            m.lastName.toLowerCase().includes(query.toLowerCase()) ||
            m.email?.toLowerCase().includes(query.toLowerCase()) ||
            m.phone?.includes(query)
          );
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Property 9: Announcement Sorting
describe('Announcement Sorting', () => {
  it('should sort pinned first, then by date descending', () => {
    fc.assert(
      fc.property(
        fc.array(announcementArbitrary),
        (announcements) => {
          const sorted = sortAnnouncements(announcements);
          // Check pinned come first
          const pinnedEnd = sorted.findIndex(a => !a.isPinned);
          const allPinnedFirst = sorted.slice(0, pinnedEnd).every(a => a.isPinned);
          // Check date ordering within groups
          const pinnedSorted = isSortedByDateDesc(sorted.filter(a => a.isPinned));
          const unpinnedSorted = isSortedByDateDesc(sorted.filter(a => !a.isPinned));
          return allPinnedFirst && pinnedSorted && unpinnedSorted;
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### Integration Tests

- Test API service with mock server
- Test authentication flow end-to-end
- Test offline/online sync scenarios
- Test navigation flows

### E2E Tests

Using Detox for React Native:

- Login flow
- Member search and contact
- Event registration
- Worship assignment confirmation
- Donation flow
