/**
 * SyncService - Offline queue management and data synchronization
 * Handles caching, offline action queuing, and connectivity monitoring
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
 */

import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import { STORAGE_KEYS, CACHE_DURATION } from '../constants';
import { QueuedAction, SyncResult, SyncConflict } from '../types/api';
import { Member, Event } from '../types/models';
import { apiService } from './ApiService';
import { storageService } from './StorageService';

export interface CachedData<T> {
  data: T;
  timestamp: number;
  isStale: boolean;
}

export interface Announcement {
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
}

type ConnectivityHandler = (isOnline: boolean) => void;

export interface SyncServiceInterface {
  // Queue management
  queueAction(action: Omit<QueuedAction, 'id' | 'createdAt' | 'retryCount'>): Promise<void>;
  getQueuedActions(): Promise<QueuedAction[]>;
  clearQueue(): Promise<void>;
  removeFromQueue(actionId: string): Promise<void>;

  // Sync operations
  syncAll(): Promise<SyncResult>;
  syncMembers(): Promise<void>;
  syncEvents(): Promise<void>;
  syncAnnouncements(): Promise<void>;

  // Cache operations
  getCachedMembers(): Promise<CachedData<Member[]> | null>;
  getCachedEvents(): Promise<CachedData<Event[]> | null>;
  getCachedAnnouncements(): Promise<CachedData<Announcement[]> | null>;

  // Status
  isOnline(): Promise<boolean>;
  getLastSyncTime(): Promise<Date | null>;
  onConnectivityChange(handler: ConnectivityHandler): () => void;
}

class SyncService implements SyncServiceInterface {
  private connectivityHandlers: ConnectivityHandler[] = [];
  private unsubscribeNetInfo: (() => void) | null = null;
  private currentOnlineStatus: boolean = true;


  constructor() {
    this.initConnectivityListener();
  }

  /**
   * Initialize network connectivity listener
   */
  private initConnectivityListener(): void {
    this.unsubscribeNetInfo = NetInfo.addEventListener((state: NetInfoState) => {
      const isOnline = state.isConnected === true && state.isInternetReachable !== false;
      
      if (this.currentOnlineStatus !== isOnline) {
        this.currentOnlineStatus = isOnline;
        this.notifyConnectivityChange(isOnline);

        // Auto-sync when coming back online
        if (isOnline) {
          this.syncQueuedActions().catch(console.error);
        }
      }
    });
  }

  /**
   * Notify all registered handlers of connectivity change
   */
  private notifyConnectivityChange(isOnline: boolean): void {
    this.connectivityHandlers.forEach((handler) => handler(isOnline));
  }

  /**
   * Generate unique ID for queued actions
   */
  private generateActionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Queue an action for later execution when offline
   * Requirements: 9.3
   */
  async queueAction(
    action: Omit<QueuedAction, 'id' | 'createdAt' | 'retryCount'>
  ): Promise<void> {
    const queuedAction: QueuedAction = {
      ...action,
      id: this.generateActionId(),
      createdAt: new Date(),
      retryCount: 0,
    };

    const queue = await this.getQueuedActions();
    queue.push(queuedAction);
    await storageService.set(STORAGE_KEYS.OFFLINE_QUEUE, queue);
  }

  /**
   * Get all queued actions
   */
  async getQueuedActions(): Promise<QueuedAction[]> {
    const queue = await storageService.get<QueuedAction[]>(STORAGE_KEYS.OFFLINE_QUEUE);
    return queue ?? [];
  }

  /**
   * Clear all queued actions
   */
  async clearQueue(): Promise<void> {
    await storageService.delete(STORAGE_KEYS.OFFLINE_QUEUE);
  }

  /**
   * Remove a specific action from the queue
   */
  async removeFromQueue(actionId: string): Promise<void> {
    const queue = await this.getQueuedActions();
    const filteredQueue = queue.filter((action) => action.id !== actionId);
    await storageService.set(STORAGE_KEYS.OFFLINE_QUEUE, filteredQueue);
  }


  /**
   * Execute queued actions when back online
   * Requirements: 9.4
   */
  private async syncQueuedActions(): Promise<{ synced: number; failed: number; conflicts: SyncConflict[] }> {
    const queue = await this.getQueuedActions();
    let synced = 0;
    let failed = 0;
    const conflicts: SyncConflict[] = [];

    for (const action of queue) {
      try {
        let response;
        
        switch (action.method) {
          case 'POST':
            response = await apiService.post(action.endpoint, action.data);
            break;
          case 'PUT':
            response = await apiService.put(action.endpoint, action.data);
            break;
          case 'DELETE':
            response = await apiService.delete(action.endpoint);
            break;
        }

        if (response.success) {
          await this.removeFromQueue(action.id);
          synced++;
        } else if (response.status === 409) {
          // Conflict detected
          conflicts.push({
            id: action.id,
            type: action.type,
            localData: action.data,
            serverData: response.data as Record<string, unknown>,
          });
          failed++;
        } else {
          // Increment retry count
          action.retryCount++;
          if (action.retryCount >= 3) {
            await this.removeFromQueue(action.id);
            failed++;
          }
        }
      } catch (error) {
        console.error(`Error syncing action ${action.id}:`, error);
        action.retryCount++;
        if (action.retryCount >= 3) {
          await this.removeFromQueue(action.id);
          failed++;
        }
      }
    }

    return { synced, failed, conflicts };
  }

  /**
   * Sync all data (members, events, announcements) and queued actions
   * Requirements: 9.4, 9.6
   */
  async syncAll(): Promise<SyncResult> {
    const isOnline = await this.isOnline();
    
    if (!isOnline) {
      return {
        success: false,
        synced: 0,
        failed: 0,
        conflicts: [],
      };
    }

    try {
      // Sync queued actions first
      const queueResult = await this.syncQueuedActions();

      // Then refresh cached data
      await Promise.all([
        this.syncMembers(),
        this.syncEvents(),
        this.syncAnnouncements(),
      ]);

      // Update last sync time
      await storageService.set(STORAGE_KEYS.LAST_SYNC, new Date().toISOString());

      return {
        success: true,
        synced: queueResult.synced,
        failed: queueResult.failed,
        conflicts: queueResult.conflicts,
      };
    } catch (error) {
      console.error('Error during sync:', error);
      return {
        success: false,
        synced: 0,
        failed: 0,
        conflicts: [],
      };
    }
  }


  /**
   * Sync members data from server
   * Requirements: 9.1
   */
  async syncMembers(): Promise<void> {
    const response = await apiService.get<Member[]>('/members/');
    
    if (response.success) {
      const cachedData: CachedData<Member[]> = {
        data: response.data,
        timestamp: Date.now(),
        isStale: false,
      };
      await storageService.set(STORAGE_KEYS.MEMBERS_CACHE, cachedData);
    }
  }

  /**
   * Sync events data from server
   * Requirements: 9.1
   */
  async syncEvents(): Promise<void> {
    const response = await apiService.get<Event[]>('/events/');
    
    if (response.success) {
      const cachedData: CachedData<Event[]> = {
        data: response.data,
        timestamp: Date.now(),
        isStale: false,
      };
      await storageService.set(STORAGE_KEYS.EVENTS_CACHE, cachedData);
    }
  }

  /**
   * Sync announcements data from server
   * Requirements: 9.1
   */
  async syncAnnouncements(): Promise<void> {
    const response = await apiService.get<Announcement[]>('/announcements/');
    
    if (response.success) {
      const cachedData: CachedData<Announcement[]> = {
        data: response.data,
        timestamp: Date.now(),
        isStale: false,
      };
      await storageService.set(STORAGE_KEYS.ANNOUNCEMENTS_CACHE, cachedData);
    }
  }

  /**
   * Get cached members with staleness check
   * Requirements: 9.1, 9.2
   */
  async getCachedMembers(): Promise<CachedData<Member[]> | null> {
    const cached = await storageService.get<CachedData<Member[]>>(STORAGE_KEYS.MEMBERS_CACHE);
    
    if (!cached) {
      return null;
    }

    // Check if cache is stale
    const isStale = Date.now() - cached.timestamp > CACHE_DURATION.MEMBERS;
    
    return {
      ...cached,
      isStale,
    };
  }

  /**
   * Get cached events with staleness check
   * Requirements: 9.1, 9.2
   */
  async getCachedEvents(): Promise<CachedData<Event[]> | null> {
    const cached = await storageService.get<CachedData<Event[]>>(STORAGE_KEYS.EVENTS_CACHE);
    
    if (!cached) {
      return null;
    }

    // Check if cache is stale
    const isStale = Date.now() - cached.timestamp > CACHE_DURATION.EVENTS;
    
    return {
      ...cached,
      isStale,
    };
  }

  /**
   * Get cached announcements with staleness check
   * Requirements: 9.1, 9.2
   */
  async getCachedAnnouncements(): Promise<CachedData<Announcement[]> | null> {
    const cached = await storageService.get<CachedData<Announcement[]>>(
      STORAGE_KEYS.ANNOUNCEMENTS_CACHE
    );
    
    if (!cached) {
      return null;
    }

    // Check if cache is stale
    const isStale = Date.now() - cached.timestamp > CACHE_DURATION.ANNOUNCEMENTS;
    
    return {
      ...cached,
      isStale,
    };
  }


  /**
   * Check current online status
   */
  async isOnline(): Promise<boolean> {
    const state = await NetInfo.fetch();
    return state.isConnected === true && state.isInternetReachable !== false;
  }

  /**
   * Get the last sync timestamp
   */
  async getLastSyncTime(): Promise<Date | null> {
    const lastSync = await storageService.get<string>(STORAGE_KEYS.LAST_SYNC);
    return lastSync ? new Date(lastSync) : null;
  }

  /**
   * Register a handler for connectivity changes
   */
  onConnectivityChange(handler: ConnectivityHandler): () => void {
    this.connectivityHandlers.push(handler);

    // Return cleanup function
    return () => {
      const index = this.connectivityHandlers.indexOf(handler);
      if (index > -1) {
        this.connectivityHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    if (this.unsubscribeNetInfo) {
      this.unsubscribeNetInfo();
      this.unsubscribeNetInfo = null;
    }
    this.connectivityHandlers = [];
  }
}

// Export singleton instance
export const syncService = new SyncService();

// Export class for testing
export { SyncService };
