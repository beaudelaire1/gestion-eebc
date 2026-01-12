# Requirements Document

## Introduction

Application mobile cross-platform pour l'Église Évangélique Baptiste de Cabassou (EEBC) permettant aux membres et responsables d'accéder aux fonctionnalités de gestion de l'église depuis leur smartphone. L'application se connecte au backend Django existant via une API REST.

## Glossary

- **App_Mobile**: L'application mobile React Native/Flutter pour iOS et Android
- **API_Backend**: L'API REST Django exposant les données du système de gestion EEBC
- **JWT_Token**: Token d'authentification JSON Web Token pour sécuriser les requêtes
- **Member**: Un membre de l'église avec un profil dans le système
- **User**: Un utilisateur authentifié avec un compte dans l'application
- **Push_Notification**: Notification envoyée au téléphone de l'utilisateur
- **Offline_Mode**: Mode de fonctionnement sans connexion internet avec synchronisation différée

## Requirements

### Requirement 1: Authentification et Sécurité

**User Story:** As a user, I want to securely log in to the mobile app, so that I can access my personalized church information.

#### Acceptance Criteria

1. WHEN a user opens the App_Mobile for the first time, THE App_Mobile SHALL display a login screen with username and password fields
2. WHEN a user submits valid credentials, THE API_Backend SHALL return a JWT_Token pair (access + refresh)
3. WHEN a user is authenticated, THE App_Mobile SHALL securely store the JWT_Token in encrypted local storage
4. WHEN a user's access token expires, THE App_Mobile SHALL automatically refresh it using the refresh token
5. WHEN a user with must_change_password flag logs in, THE App_Mobile SHALL redirect to a password change screen
6. WHEN a user taps logout, THE App_Mobile SHALL clear all stored tokens and return to login screen
7. IF biometric authentication is available, THEN THE App_Mobile SHALL offer fingerprint/face unlock option
8. WHEN 5 consecutive login attempts fail, THE App_Mobile SHALL display account locked message with remaining time

### Requirement 2: Dashboard Personnel

**User Story:** As a member, I want to see a personalized dashboard, so that I can quickly access relevant information and actions.

#### Acceptance Criteria

1. WHEN a user logs in successfully, THE App_Mobile SHALL display a dashboard with role-appropriate widgets
2. THE Dashboard SHALL display upcoming events for the next 7 days
3. THE Dashboard SHALL display unread announcements count with preview
4. WHEN the user has worship assignments, THE Dashboard SHALL display next scheduled service role
5. WHEN the user is a parent, THE Dashboard SHALL display BibleClub attendance summary for their children
6. THE Dashboard SHALL provide quick action buttons based on user role
7. WHEN new data is available, THE App_Mobile SHALL update dashboard via pull-to-refresh gesture

### Requirement 3: Annuaire des Membres

**User Story:** As a member, I want to browse and search the church directory, so that I can find and contact other members.

#### Acceptance Criteria

1. WHEN a user navigates to the directory, THE App_Mobile SHALL display a searchable list of active members
2. WHEN a user types in the search field, THE App_Mobile SHALL filter members by name, phone, or email in real-time
3. WHEN a user taps on a member, THE App_Mobile SHALL display the member's profile with photo, contact info, and family links
4. WHEN a user taps the phone icon, THE App_Mobile SHALL initiate a phone call to that member
5. WHEN a user taps the WhatsApp icon, THE App_Mobile SHALL open WhatsApp with that member's number
6. WHEN a user taps the email icon, THE App_Mobile SHALL open the email client with that member's address
7. THE App_Mobile SHALL respect privacy settings and only show information the user is authorized to see
8. WHEN offline, THE App_Mobile SHALL display cached member data with a sync indicator

### Requirement 4: Événements et Calendrier

**User Story:** As a member, I want to view church events and register for them, so that I can participate in church activities.

#### Acceptance Criteria

1. WHEN a user navigates to events, THE App_Mobile SHALL display a calendar view with event markers
2. WHEN a user taps on a date, THE App_Mobile SHALL show events scheduled for that day
3. WHEN a user taps on an event, THE App_Mobile SHALL display event details (title, date, time, location, description)
4. WHEN an event allows registration, THE App_Mobile SHALL display a register button
5. WHEN a user registers for an event, THE API_Backend SHALL record the registration and confirm
6. WHEN an event is within 24 hours, THE App_Mobile SHALL send a Push_Notification reminder
7. THE App_Mobile SHALL allow users to add events to their device calendar
8. WHEN a user is registered for an event, THE App_Mobile SHALL display a "registered" badge

### Requirement 5: Planning Culte (Worship)

**User Story:** As a worship team member, I want to view my service assignments, so that I can prepare and confirm my availability.

#### Acceptance Criteria

1. WHEN a user navigates to worship planning, THE App_Mobile SHALL display upcoming services with their assignments
2. WHEN a user has an assignment, THE App_Mobile SHALL highlight their role in the service
3. WHEN a user taps on a service, THE App_Mobile SHALL display full team roster and song list
4. THE App_Mobile SHALL allow users to confirm or decline their assignment
5. WHEN a user declines, THE App_Mobile SHALL prompt for a reason and notify the worship leader
6. WHEN assignments change, THE App_Mobile SHALL send a Push_Notification to affected users
7. THE App_Mobile SHALL display service history for the past 3 months

### Requirement 6: Annonces et Communication

**User Story:** As a member, I want to receive church announcements, so that I can stay informed about church news and updates.

#### Acceptance Criteria

1. WHEN a new announcement is published, THE App_Mobile SHALL receive a Push_Notification
2. WHEN a user navigates to announcements, THE App_Mobile SHALL display a list sorted by date (newest first)
3. WHEN a user taps an announcement, THE App_Mobile SHALL display full content with images if any
4. THE App_Mobile SHALL mark announcements as read when viewed
5. WHEN an announcement is pinned, THE App_Mobile SHALL display it at the top of the list
6. THE App_Mobile SHALL allow users to share announcements via native share sheet
7. WHEN offline, THE App_Mobile SHALL display cached announcements

### Requirement 7: Dons et Finance

**User Story:** As a member, I want to make donations and view my giving history, so that I can support the church financially.

#### Acceptance Criteria

1. WHEN a user navigates to giving, THE App_Mobile SHALL display donation options (tithe, offering, special funds)
2. WHEN a user initiates a donation, THE App_Mobile SHALL integrate with Stripe for secure payment
3. WHEN a donation is successful, THE API_Backend SHALL record the transaction and send confirmation
4. THE App_Mobile SHALL display the user's donation history for the current year
5. WHEN tax receipts are available, THE App_Mobile SHALL allow users to download them as PDF
6. THE App_Mobile SHALL support recurring donation setup
7. IF payment fails, THEN THE App_Mobile SHALL display a clear error message and retry option

### Requirement 8: Notifications Push

**User Story:** As a member, I want to receive push notifications, so that I can be alerted to important church updates in real-time.

#### Acceptance Criteria

1. WHEN the app is installed, THE App_Mobile SHALL request push notification permission
2. WHEN permission is granted, THE App_Mobile SHALL register the device token with the API_Backend
3. THE App_Mobile SHALL receive notifications for: new announcements, event reminders, worship assignments, donation confirmations
4. THE App_Mobile SHALL allow users to configure notification preferences per category
5. WHEN a notification is tapped, THE App_Mobile SHALL navigate to the relevant content
6. THE App_Mobile SHALL display notification badge count on the app icon

### Requirement 9: Mode Hors-ligne

**User Story:** As a member, I want to use the app offline, so that I can access information even without internet connection.

#### Acceptance Criteria

1. THE App_Mobile SHALL cache essential data locally (members, events, announcements)
2. WHEN offline, THE App_Mobile SHALL display cached data with a visual offline indicator
3. WHEN offline, THE App_Mobile SHALL queue actions (registrations, confirmations) for later sync
4. WHEN connection is restored, THE App_Mobile SHALL automatically sync queued actions
5. IF sync conflicts occur, THEN THE App_Mobile SHALL notify the user and offer resolution options
6. THE App_Mobile SHALL refresh cache when online and app is opened

### Requirement 10: Profil Utilisateur

**User Story:** As a user, I want to manage my profile and preferences, so that I can keep my information up to date.

#### Acceptance Criteria

1. WHEN a user navigates to profile, THE App_Mobile SHALL display their current information
2. THE App_Mobile SHALL allow users to update their photo, phone, and email
3. THE App_Mobile SHALL allow users to change their password
4. THE App_Mobile SHALL allow users to configure notification preferences
5. THE App_Mobile SHALL allow users to toggle dark mode
6. THE App_Mobile SHALL display app version and provide feedback/support link
7. WHEN profile changes are saved, THE API_Backend SHALL update the member record
