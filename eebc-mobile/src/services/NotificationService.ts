/**
 * NotificationService - Push notification management
 * Handles permission requests, device registration, and notification handlers
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import { STORAGE_KEYS, NOTIFICATION_CHANNELS } from '../constants';
import { apiService } from './ApiService';
import { storageService } from './StorageService';

export interface LocalNotification {
  title: string;
  body: string;
  data?: Record<string, unknown>;
  trigger: { date: Date } | { seconds: number };
}

export interface NotificationPreferences {
  [NOTIFICATION_CHANNELS.ANNOUNCEMENTS]: boolean;
  [NOTIFICATION_CHANNELS.EVENTS]: boolean;
  [NOTIFICATION_CHANNELS.WORSHIP]: boolean;
  [NOTIFICATION_CHANNELS.DONATIONS]: boolean;
}

export type NotificationHandler = (notification: Notifications.Notification) => void;
export type NotificationResponseHandler = (response: Notifications.NotificationResponse) => void;

export interface NotificationServiceInterface {
  requestPermission(): Promise<boolean>;
  registerDevice(userId: number): Promise<void>;
  unregisterDevice(): Promise<void>;
  getDeviceToken(): Promise<string | null>;
  scheduleLocalNotification(notification: LocalNotification): Promise<string>;
  cancelNotification(id: string): Promise<void>;
  cancelAllNotifications(): Promise<void>;
  onNotificationReceived(handler: NotificationHandler): () => void;
  onNotificationTapped(handler: NotificationResponseHandler): () => void;
  getPreferences(): Promise<NotificationPreferences>;
  setPreferences(preferences: NotificationPreferences): Promise<void>;
  getBadgeCount(): Promise<number>;
  setBadgeCount(count: number): Promise<void>;
}

// Default notification preferences
const DEFAULT_PREFERENCES: NotificationPreferences = {
  [NOTIFICATION_CHANNELS.ANNOUNCEMENTS]: true,
  [NOTIFICATION_CHANNELS.EVENTS]: true,
  [NOTIFICATION_CHANNELS.WORSHIP]: true,
  [NOTIFICATION_CHANNELS.DONATIONS]: true,
};

class NotificationService implements NotificationServiceInterface {
  private deviceToken: string | null = null;
  private notificationListener: Notifications.Subscription | null = null;
  private responseListener: Notifications.Subscription | null = null;
  private fcmUnsubscribe: (() => void) | null = null;
  private fcmBackgroundUnsubscribe: (() => void) | null = null;

  constructor() {
    this.configureNotifications();
    this.setupFirebaseMessaging();
  }


  /**
   * Configure notification handling behavior
   */
  private configureNotifications(): void {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
      }),
    });
  }

  /**
   * Setup Firebase Cloud Messaging handlers
   */
  private setupFirebaseMessaging(): void {
    // Handle background messages
    messaging().setBackgroundMessageHandler(async (remoteMessage) => {
      console.log('Message handled in the background!', remoteMessage);
      
      // Update badge count if provided
      if (remoteMessage.data?.badge) {
        const badgeCount = parseInt(remoteMessage.data.badge as string, 10);
        await this.setBadgeCount(badgeCount);
      }
    });

    // Handle foreground messages
    this.fcmUnsubscribe = messaging().onMessage(async (remoteMessage) => {
      console.log('A new FCM message arrived!', remoteMessage);
      
      // Show local notification for foreground messages
      if (remoteMessage.notification) {
        await Notifications.scheduleNotificationAsync({
          content: {
            title: remoteMessage.notification.title || 'Notification',
            body: remoteMessage.notification.body || '',
            data: remoteMessage.data,
            sound: true,
          },
          trigger: null, // Show immediately
        });
      }
    });

    // Handle notification opened app
    messaging().onNotificationOpenedApp((remoteMessage) => {
      console.log(
        'Notification caused app to open from background state:',
        remoteMessage.notification,
      );
      
      // Handle deep linking here
      this.handleNotificationNavigation(remoteMessage);
    });

    // Check whether an initial notification is available
    messaging()
      .getInitialNotification()
      .then((remoteMessage) => {
        if (remoteMessage) {
          console.log(
            'Notification caused app to open from quit state:',
            remoteMessage.notification,
          );
          
          // Handle deep linking here
          this.handleNotificationNavigation(remoteMessage);
        }
      });

    // Handle token refresh
    messaging().onTokenRefresh(async (token) => {
      console.log('FCM token refreshed:', token);
      this.deviceToken = token;
      await storageService.set('device_push_token', token);
      
      // Re-register with backend if user is logged in
      // This would need to be handled by the auth service
    });
  }

  /**
   * Handle navigation from notification tap
   */
  private handleNotificationNavigation(remoteMessage: any): void {
    // This will be implemented in the deep linking property test
    // For now, just log the navigation data
    console.log('Navigation data:', remoteMessage.data);
  }

  /**
   * Request notification permission from the user
   * Requirements: 8.1
   */
  async requestPermission(): Promise<boolean> {
    // Request Firebase messaging permission
    const authStatus = await messaging().requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;

    if (!enabled) {
      return false;
    }

    // Also request Expo notifications permission for local notifications
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    
    let finalStatus = existingStatus;
    
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    // Get and store the device token
    await this.fetchDeviceToken();
    
    return finalStatus === 'granted' && enabled;
  }

  /**
   * Fetch and store the device push token
   */
  private async fetchDeviceToken(): Promise<void> {
    try {
      // For Android, we need to set up a notification channel
      if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
          name: 'default',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#FF231F7C',
        });
      }

      // Get Firebase Cloud Messaging token
      const fcmToken = await messaging().getToken();
      
      this.deviceToken = fcmToken;
      await storageService.set('device_push_token', this.deviceToken);
    } catch (error) {
      console.error('Error fetching device token:', error);
    }
  }

  /**
   * Register device token with the backend
   * Requirements: 8.2
   */
  async registerDevice(userId: number): Promise<void> {
    if (!this.deviceToken) {
      await this.fetchDeviceToken();
    }

    if (!this.deviceToken) {
      throw new Error('Impossible d\'obtenir le token de notification');
    }

    const response = await apiService.post('/notifications/register/', {
      token: this.deviceToken,
      user_id: userId,
      platform: Platform.OS,
    });

    if (!response.success) {
      throw new Error(response.error || 'Échec de l\'enregistrement du device');
    }
  }

  /**
   * Unregister device from push notifications
   */
  async unregisterDevice(): Promise<void> {
    if (this.deviceToken) {
      await apiService.post('/notifications/unregister/', {
        token: this.deviceToken,
      });
    }

    this.deviceToken = null;
    await storageService.delete('device_push_token');
  }

  /**
   * Get the current device token
   */
  async getDeviceToken(): Promise<string | null> {
    if (this.deviceToken) {
      return this.deviceToken;
    }

    // Try to get from storage
    const storedToken = await storageService.get<string>('device_push_token');
    if (storedToken) {
      this.deviceToken = storedToken;
    }

    return this.deviceToken;
  }


  /**
   * Schedule a local notification
   * Requirements: 8.3 (for event reminders)
   */
  async scheduleLocalNotification(notification: LocalNotification): Promise<string> {
    let trigger: Notifications.NotificationTriggerInput;

    if ('date' in notification.trigger) {
      trigger = {
        date: notification.trigger.date,
      };
    } else {
      trigger = {
        seconds: notification.trigger.seconds,
      };
    }

    const id = await Notifications.scheduleNotificationAsync({
      content: {
        title: notification.title,
        body: notification.body,
        data: notification.data,
        sound: true,
      },
      trigger,
    });

    return id;
  }

  /**
   * Cancel a scheduled notification
   */
  async cancelNotification(id: string): Promise<void> {
    await Notifications.cancelScheduledNotificationAsync(id);
  }

  /**
   * Cancel all scheduled notifications
   */
  async cancelAllNotifications(): Promise<void> {
    await Notifications.cancelAllScheduledNotificationsAsync();
  }

  /**
   * Set handler for notifications received while app is in foreground
   * Requirements: 8.3
   */
  onNotificationReceived(handler: NotificationHandler): () => void {
    // Remove existing listener if any
    if (this.notificationListener) {
      this.notificationListener.remove();
    }

    this.notificationListener = Notifications.addNotificationReceivedListener(handler);

    // Return cleanup function
    return () => {
      if (this.notificationListener) {
        this.notificationListener.remove();
        this.notificationListener = null;
      }
    };
  }

  /**
   * Set handler for when user taps on a notification
   * Requirements: 8.5
   */
  onNotificationTapped(handler: NotificationResponseHandler): () => void {
    // Remove existing listener if any
    if (this.responseListener) {
      this.responseListener.remove();
    }

    this.responseListener = Notifications.addNotificationResponseReceivedListener(handler);

    // Return cleanup function
    return () => {
      if (this.responseListener) {
        this.responseListener.remove();
        this.responseListener = null;
      }
    };
  }

  /**
   * Get notification preferences
   * Requirements: 8.4
   */
  async getPreferences(): Promise<NotificationPreferences> {
    const preferences = await storageService.get<NotificationPreferences>(
      STORAGE_KEYS.NOTIFICATION_PREFERENCES
    );
    return preferences ?? DEFAULT_PREFERENCES;
  }

  /**
   * Set notification preferences
   * Requirements: 8.4
   */
  async setPreferences(preferences: NotificationPreferences): Promise<void> {
    await storageService.set(STORAGE_KEYS.NOTIFICATION_PREFERENCES, preferences);

    // Sync preferences with backend
    await apiService.put('/notifications/preferences/', {
      preferences,
    });
  }

  /**
   * Get current badge count
   * Requirements: 8.6
   */
  async getBadgeCount(): Promise<number> {
    return await Notifications.getBadgeCountAsync();
  }

  /**
   * Set badge count on app icon
   * Requirements: 8.6
   */
  async setBadgeCount(count: number): Promise<void> {
    await Notifications.setBadgeCountAsync(count);
  }

  /**
   * Clear all listeners (call on cleanup)
   */
  cleanup(): void {
    if (this.notificationListener) {
      this.notificationListener.remove();
      this.notificationListener = null;
    }
    if (this.responseListener) {
      this.responseListener.remove();
      this.responseListener = null;
    }
    if (this.fcmUnsubscribe) {
      this.fcmUnsubscribe();
      this.fcmUnsubscribe = null;
    }
    if (this.fcmBackgroundUnsubscribe) {
      this.fcmBackgroundUnsubscribe();
      this.fcmBackgroundUnsubscribe = null;
    }
  }
}

// Export singleton instance
export const notificationService = new NotificationService();

// Export class for testing
export { NotificationService };
