/**
 * useNotifications - React hook for notification management
 * Provides easy access to notification functionality in components
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
 */

import { useEffect, useCallback, useState } from 'react';
import * as Notifications from 'expo-notifications';
import { notificationService, NotificationPreferences } from '../services/NotificationService';

export interface UseNotificationsReturn {
  // Permission and registration
  requestPermission: () => Promise<boolean>;
  registerDevice: (userId: number) => Promise<void>;
  isPermissionGranted: boolean;
  
  // Preferences
  preferences: NotificationPreferences | null;
  updatePreferences: (preferences: NotificationPreferences) => Promise<void>;
  
  // Badge count
  badgeCount: number;
  setBadgeCount: (count: number) => Promise<void>;
  
  // Local notifications
  scheduleLocalNotification: (notification: {
    title: string;
    body: string;
    data?: Record<string, unknown>;
    trigger: { date: Date } | { seconds: number };
  }) => Promise<string>;
  cancelNotification: (id: string) => Promise<void>;
  
  // Status
  isLoading: boolean;
  error: string | null;
}

export const useNotifications = (): UseNotificationsReturn => {
  const [isPermissionGranted, setIsPermissionGranted] = useState(false);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [badgeCount, setBadgeCountState] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check initial permission status
  useEffect(() => {
    const checkPermission = async () => {
      try {
        const { status } = await Notifications.getPermissionsAsync();
        setIsPermissionGranted(status === 'granted');
        
        // Load preferences
        const prefs = await notificationService.getPreferences();
        setPreferences(prefs);
        
        // Load badge count
        const count = await notificationService.getBadgeCount();
        setBadgeCountState(count);
      } catch (err) {
        console.error('Error checking notification permission:', err);
      }
    };

    checkPermission();
  }, []);

  // Set up notification handlers
  useEffect(() => {
    // Handle notifications received while app is in foreground
    const unsubscribeReceived = notificationService.onNotificationReceived(
      (notification) => {
        console.log('Notification received:', notification);
        // You can add custom handling here
      }
    );

    // Handle notification taps
    const unsubscribeTapped = notificationService.onNotificationTapped(
      (response) => {
        console.log('Notification tapped:', response);
        // Navigation will be handled by the deep linking logic
      }
    );

    return () => {
      unsubscribeReceived();
      unsubscribeTapped();
    };
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const granted = await notificationService.requestPermission();
      setIsPermissionGranted(granted);
      return granted;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur lors de la demande de permission';
      setError(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const registerDevice = useCallback(async (userId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      await notificationService.registerDevice(userId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur lors de l\'enregistrement du device';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updatePreferences = useCallback(async (newPreferences: NotificationPreferences): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      await notificationService.setPreferences(newPreferences);
      setPreferences(newPreferences);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur lors de la mise à jour des préférences';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setBadgeCount = useCallback(async (count: number): Promise<void> => {
    try {
      await notificationService.setBadgeCount(count);
      setBadgeCountState(count);
    } catch (err) {
      console.error('Error setting badge count:', err);
    }
  }, []);

  const scheduleLocalNotification = useCallback(async (notification: {
    title: string;
    body: string;
    data?: Record<string, unknown>;
    trigger: { date: Date } | { seconds: number };
  }): Promise<string> => {
    setError(null);
    
    try {
      return await notificationService.scheduleLocalNotification(notification);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur lors de la programmation de la notification';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const cancelNotification = useCallback(async (id: string): Promise<void> => {
    try {
      await notificationService.cancelNotification(id);
    } catch (err) {
      console.error('Error canceling notification:', err);
    }
  }, []);

  return {
    requestPermission,
    registerDevice,
    isPermissionGranted,
    preferences,
    updatePreferences,
    badgeCount,
    setBadgeCount,
    scheduleLocalNotification,
    cancelNotification,
    isLoading,
    error,
  };
};