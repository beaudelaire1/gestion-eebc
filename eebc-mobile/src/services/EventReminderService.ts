/**
 * EventReminderService - Manages event reminder notifications
 * Requirements: 4.6
 */

import { notificationService, LocalNotification } from './NotificationService';
import { storageService } from './StorageService';
import { Event } from '../types/models';

const REMINDER_STORAGE_KEY = 'event_reminders';

interface ScheduledReminder {
  eventId: number;
  notificationId: string;
  scheduledFor: string;
}

/**
 * Format time for display in notification
 */
const formatTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

class EventReminderService {
  /**
   * Schedule a reminder notification 24 hours before an event
   * Requirements: 4.6
   */
  async scheduleReminder(event: Event): Promise<string | null> {
    const eventDate = new Date(event.startDate);
    const reminderDate = new Date(eventDate.getTime() - 24 * 60 * 60 * 1000); // 24 hours before
    
    // Don't schedule if the reminder time has already passed
    if (reminderDate <= new Date()) {
      console.log('Reminder time has already passed, not scheduling');
      return null;
    }

    // Check if a reminder is already scheduled for this event
    const existingReminder = await this.getReminderForEvent(event.id);
    if (existingReminder) {
      console.log('Reminder already scheduled for event:', event.id);
      return existingReminder.notificationId;
    }

    try {
      const notification: LocalNotification = {
        title: '📅 Rappel d\'événement',
        body: `${event.title} commence demain à ${formatTime(event.startDate)}`,
        data: {
          type: 'event_reminder',
          eventId: event.id,
          eventTitle: event.title,
        },
        trigger: { date: reminderDate },
      };

      const notificationId = await notificationService.scheduleLocalNotification(notification);

      // Store the reminder info
      await this.saveReminder({
        eventId: event.id,
        notificationId,
        scheduledFor: reminderDate.toISOString(),
      });

      console.log('Scheduled reminder for event:', event.id, 'at:', reminderDate);
      return notificationId;
    } catch (error) {
      console.error('Failed to schedule reminder:', error);
      return null;
    }
  }

  /**
   * Cancel a scheduled reminder for an event
   */
  async cancelReminder(eventId: number): Promise<void> {
    const reminder = await this.getReminderForEvent(eventId);
    
    if (reminder) {
      try {
        await notificationService.cancelNotification(reminder.notificationId);
        await this.removeReminder(eventId);
        console.log('Cancelled reminder for event:', eventId);
      } catch (error) {
        console.error('Failed to cancel reminder:', error);
      }
    }
  }

  /**
   * Get all scheduled reminders
   */
  async getAllReminders(): Promise<ScheduledReminder[]> {
    const reminders = await storageService.get<ScheduledReminder[]>(REMINDER_STORAGE_KEY);
    return reminders ?? [];
  }

  /**
   * Get reminder for a specific event
   */
  async getReminderForEvent(eventId: number): Promise<ScheduledReminder | null> {
    const reminders = await this.getAllReminders();
    return reminders.find(r => r.eventId === eventId) ?? null;
  }

  /**
   * Check if a reminder is scheduled for an event
   */
  async hasReminder(eventId: number): Promise<boolean> {
    const reminder = await this.getReminderForEvent(eventId);
    return reminder !== null;
  }

  /**
   * Save a reminder to storage
   */
  private async saveReminder(reminder: ScheduledReminder): Promise<void> {
    const reminders = await this.getAllReminders();
    const updatedReminders = [...reminders.filter(r => r.eventId !== reminder.eventId), reminder];
    await storageService.set(REMINDER_STORAGE_KEY, updatedReminders);
  }

  /**
   * Remove a reminder from storage
   */
  private async removeReminder(eventId: number): Promise<void> {
    const reminders = await this.getAllReminders();
    const updatedReminders = reminders.filter(r => r.eventId !== eventId);
    await storageService.set(REMINDER_STORAGE_KEY, updatedReminders);
  }

  /**
   * Clean up expired reminders (reminders for past events)
   */
  async cleanupExpiredReminders(): Promise<void> {
    const reminders = await this.getAllReminders();
    const now = new Date();
    
    const expiredReminders = reminders.filter(r => new Date(r.scheduledFor) < now);
    
    for (const reminder of expiredReminders) {
      await this.removeReminder(reminder.eventId);
    }

    console.log('Cleaned up', expiredReminders.length, 'expired reminders');
  }

  /**
   * Schedule reminders for all registered events
   * Call this when the app starts or when events are synced
   */
  async scheduleRemindersForRegisteredEvents(events: Event[]): Promise<void> {
    const registeredEvents = events.filter(e => e.isUserRegistered);
    
    for (const event of registeredEvents) {
      await this.scheduleReminder(event);
    }
  }
}

// Export singleton instance
export const eventReminderService = new EventReminderService();

// Export class for testing
export { EventReminderService };
