/**
 * Announcements Store - Zustand store for announcements management
 * Requirements: 6.1, 6.2, 6.4, 6.5
 */

import { create } from 'zustand';
import { Announcement } from '../types/announcements';
import { PaginatedResponse } from '../types/api';
import { apiService } from '../services/ApiService';
import { storageService } from '../services/StorageService';
import { STORAGE_KEYS, CACHE_DURATION } from '../constants';

interface CachedData<T> {
  data: T;
  timestamp: number;
}

interface ReadStatusMap {
  [announcementId: number]: boolean;
}

interface AnnouncementsState {
  // State
  announcements: Announcement[];
  sortedAnnouncements: Announcement[];
  unreadCount: number;
  readStatus: ReadStatusMap;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastFetched: number | null;

  // Actions
  fetchAnnouncements: (forceRefresh?: boolean) => Promise<void>;
  markAsRead: (announcementId: number) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  getAnnouncementById: (id: number) => Announcement | undefined;
  getUnreadCount: () => number;
  refreshAnnouncements: () => Promise<void>;
  clearCache: () => Promise<void>;
}

const READ_STATUS_KEY = 'announcements_read_status';

/**
 * Sort announcements: pinned first, then by date descending
 * Requirements: 6.2, 6.5
 */
export function sortAnnouncements(announcements: Announcement[]): Announcement[] {
  return [...announcements].sort((a, b) => {
    // Pinned announcements come first
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;

    // Within same pinned status, sort by date descending (newest first)
    const dateA = new Date(a.publishedAt).getTime();
    const dateB = new Date(b.publishedAt).getTime();
    return dateB - dateA;
  });
}

/**
 * Calculate unread count
 */
export function calculateUnreadCount(
  announcements: Announcement[],
  readStatus: ReadStatusMap
): number {
  return announcements.filter(
    (announcement) => !announcement.isRead && !readStatus[announcement.id]
  ).length;
}

/**
 * Apply read status to announcements
 */
export function applyReadStatus(
  announcements: Announcement[],
  readStatus: ReadStatusMap
): Announcement[] {
  return announcements.map((announcement) => ({
    ...announcement,
    isRead: announcement.isRead || readStatus[announcement.id] === true,
  }));
}

export const useAnnouncementsStore = create<AnnouncementsState>((set, get) => ({
  // Initial state
  announcements: [],
  sortedAnnouncements: [],
  unreadCount: 0,
  readStatus: {},
  isLoading: false,
  isRefreshing: false,
  error: null,
  lastFetched: null,

  /**
   * Fetch announcements from API or cache
   * Requirements: 6.1
   */
  fetchAnnouncements: async (forceRefresh = false): Promise<void> => {
    const { lastFetched, readStatus } = get();

    // Load read status from storage
    const storedReadStatus = await storageService.get<ReadStatusMap>(READ_STATUS_KEY);
    const currentReadStatus = storedReadStatus ?? readStatus;

    // Check if cache is still valid
    if (!forceRefresh && lastFetched) {
      const cacheAge = Date.now() - lastFetched;
      if (cacheAge < CACHE_DURATION.ANNOUNCEMENTS) {
        return;
      }
    }

    // Try to load from cache first
    if (!forceRefresh) {
      const cached = await storageService.get<CachedData<Announcement[]>>(
        STORAGE_KEYS.ANNOUNCEMENTS_CACHE
      );

      if (cached && Date.now() - cached.timestamp < CACHE_DURATION.ANNOUNCEMENTS) {
        const announcementsWithReadStatus = applyReadStatus(cached.data, currentReadStatus);
        const sorted = sortAnnouncements(announcementsWithReadStatus);
        const unreadCount = calculateUnreadCount(announcementsWithReadStatus, currentReadStatus);

        set({
          announcements: announcementsWithReadStatus,
          sortedAnnouncements: sorted,
          unreadCount,
          readStatus: currentReadStatus,
          lastFetched: cached.timestamp,
        });
        return;
      }
    }

    set({ isLoading: true, error: null });

    try {
      const response = await apiService.get<PaginatedResponse<Announcement>>(
        '/announcements/'
      );

      if (response.success) {
        const announcements = response.data.results;
        const announcementsWithReadStatus = applyReadStatus(announcements, currentReadStatus);
        const sorted = sortAnnouncements(announcementsWithReadStatus);
        const unreadCount = calculateUnreadCount(announcementsWithReadStatus, currentReadStatus);

        // Cache the data
        await storageService.set(STORAGE_KEYS.ANNOUNCEMENTS_CACHE, {
          data: announcements,
          timestamp: Date.now(),
        });

        set({
          announcements: announcementsWithReadStatus,
          sortedAnnouncements: sorted,
          unreadCount,
          readStatus: currentReadStatus,
          isLoading: false,
          lastFetched: Date.now(),
        });
      } else {
        // Try to use cached data on error
        const cached = await storageService.get<CachedData<Announcement[]>>(
          STORAGE_KEYS.ANNOUNCEMENTS_CACHE
        );

        if (cached) {
          const announcementsWithReadStatus = applyReadStatus(cached.data, currentReadStatus);
          const sorted = sortAnnouncements(announcementsWithReadStatus);
          const unreadCount = calculateUnreadCount(announcementsWithReadStatus, currentReadStatus);

          set({
            announcements: announcementsWithReadStatus,
            sortedAnnouncements: sorted,
            unreadCount,
            readStatus: currentReadStatus,
            isLoading: false,
            error: 'Données hors ligne',
          });
        } else {
          set({
            isLoading: false,
            error: response.error ?? 'Erreur lors du chargement des annonces',
          });
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';

      // Try to use cached data on error
      const cached = await storageService.get<CachedData<Announcement[]>>(
        STORAGE_KEYS.ANNOUNCEMENTS_CACHE
      );

      if (cached) {
        const announcementsWithReadStatus = applyReadStatus(cached.data, currentReadStatus);
        const sorted = sortAnnouncements(announcementsWithReadStatus);
        const unreadCount = calculateUnreadCount(announcementsWithReadStatus, currentReadStatus);

        set({
          announcements: announcementsWithReadStatus,
          sortedAnnouncements: sorted,
          unreadCount,
          readStatus: currentReadStatus,
          isLoading: false,
          error: 'Mode hors ligne',
        });
      } else {
        set({
          isLoading: false,
          error: errorMessage,
        });
      }
    }
  },

  /**
   * Mark an announcement as read
   * Requirements: 6.4
   */
  markAsRead: async (announcementId: number): Promise<void> => {
    const { announcements, readStatus } = get();

    // Update read status
    const newReadStatus = {
      ...readStatus,
      [announcementId]: true,
    };

    // Update announcements
    const updatedAnnouncements = announcements.map((announcement) =>
      announcement.id === announcementId
        ? { ...announcement, isRead: true }
        : announcement
    );

    const sorted = sortAnnouncements(updatedAnnouncements);
    const unreadCount = calculateUnreadCount(updatedAnnouncements, newReadStatus);

    // Persist read status
    await storageService.set(READ_STATUS_KEY, newReadStatus);

    set({
      announcements: updatedAnnouncements,
      sortedAnnouncements: sorted,
      unreadCount,
      readStatus: newReadStatus,
    });

    // Optionally notify the server (fire and forget)
    apiService.post(`/announcements/${announcementId}/read/`, {}).catch(() => {
      // Ignore errors - read status is persisted locally
    });
  },

  /**
   * Mark all announcements as read
   */
  markAllAsRead: async (): Promise<void> => {
    const { announcements } = get();

    // Update read status for all
    const newReadStatus: ReadStatusMap = {};
    announcements.forEach((announcement) => {
      newReadStatus[announcement.id] = true;
    });

    // Update announcements
    const updatedAnnouncements = announcements.map((announcement) => ({
      ...announcement,
      isRead: true,
    }));

    const sorted = sortAnnouncements(updatedAnnouncements);

    // Persist read status
    await storageService.set(READ_STATUS_KEY, newReadStatus);

    set({
      announcements: updatedAnnouncements,
      sortedAnnouncements: sorted,
      unreadCount: 0,
      readStatus: newReadStatus,
    });
  },

  /**
   * Get an announcement by ID
   */
  getAnnouncementById: (id: number): Announcement | undefined => {
    const { announcements } = get();
    return announcements.find((a) => a.id === id);
  },

  /**
   * Get current unread count
   */
  getUnreadCount: (): number => {
    return get().unreadCount;
  },

  /**
   * Refresh announcements (pull-to-refresh)
   */
  refreshAnnouncements: async (): Promise<void> => {
    set({ isRefreshing: true });
    await get().fetchAnnouncements(true);
    set({ isRefreshing: false });
  },

  /**
   * Clear cached announcements data
   */
  clearCache: async (): Promise<void> => {
    await storageService.delete(STORAGE_KEYS.ANNOUNCEMENTS_CACHE);
    await storageService.delete(READ_STATUS_KEY);
    set({
      announcements: [],
      sortedAnnouncements: [],
      unreadCount: 0,
      readStatus: {},
      lastFetched: null,
    });
  },
}));
