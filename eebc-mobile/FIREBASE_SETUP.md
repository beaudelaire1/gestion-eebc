# Firebase Setup Instructions

## Prerequisites

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Cloud Messaging in the Firebase console

## Android Setup

1. In the Firebase console, add an Android app with package name: `org.eglise_ebc.mobile`
2. Download the `google-services.json` file
3. Replace the placeholder `google-services.json` file in the project root
4. Update the following values in `google-services.json`:
   - `project_number`: Your Firebase project number
   - `project_id`: Your Firebase project ID
   - `mobilesdk_app_id`: Your Android app ID
   - `android_client_info.package_name`: `org.eglise_ebc.mobile`
   - `api_key.current_key`: Your Android API key

## iOS Setup

1. In the Firebase console, add an iOS app with bundle ID: `org.eglise-ebc.mobile`
2. Download the `GoogleService-Info.plist` file
3. Replace the placeholder `GoogleService-Info.plist` file in the project root
4. Update the following values in `GoogleService-Info.plist`:
   - `CLIENT_ID`: Your iOS client ID
   - `REVERSED_CLIENT_ID`: Your reversed client ID
   - `API_KEY`: Your iOS API key
   - `GCM_SENDER_ID`: Your project number
   - `BUNDLE_ID`: `org.eglise-ebc.mobile`
   - `PROJECT_ID`: Your Firebase project ID
   - `GOOGLE_APP_ID`: Your iOS app ID

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
EXPO_PUBLIC_FIREBASE_API_KEY=your_api_key
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com
EXPO_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET=your_project_id.appspot.com
EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
EXPO_PUBLIC_FIREBASE_APP_ID=your_app_id
```

## Installation

After setting up the configuration files, run:

```bash
npm install
# or
yarn install
```

## Testing

To test Firebase Cloud Messaging:

1. Build and run the app on a physical device (FCM doesn't work on simulators)
2. Grant notification permissions when prompted
3. Check the console logs for the device token
4. Use the Firebase console to send a test notification