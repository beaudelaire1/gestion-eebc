/**
 * Members Store - Zustand store for member directory management
 * Requirements: 3.1, 3.2
 */

import { create } from 'zustand';
import { Member } from '../types/models';
import { PaginatedResponse } from '../types/api';
import { apiService } from '../services/ApiService';
import { storageService } from '../services/StorageService';
import { STORAGE_KEYS, CACHE_DURATION } from '../constants';

interface CachedData<T> {
  data: T;
  timestamp: number;
}

interface MembersState {
  // State
  members: Member[];
  filteredMembers: Member[];
  searchQuery: string;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastFetched: number | null;

  // Actions
  fetchMembers: (forceRefresh?: boolean) => Promise<void>;
  setSearchQuery: (query: string) => void;
  getMemberById: (id: number) => Member | undefined;
  refreshMembers: () => Promise<void>;
  clearCache: () => Promise<void>;
}

/**
 * Filter members by search query
 * Searches in firstName, lastName, email, and phone
 * Requirements: 3.2
 */
export function filterMembers(members: Member[], query: string): Member[] {
  if (!query || query.trim() === '') {
    return members;
  }

  const normalizedQuery = query.toLowerCase().trim();

  return members.filter((member) => {
    const firstName = member.firstName?.toLowerCase() ?? '';
    const lastName = member.lastName?.toLowerCase() ?? '';
    const email = member.email?.toLowerCase() ?? '';
    const phone = member.phone ?? '';

    return (
      firstName.includes(normalizedQuery) ||
      lastName.includes(normalizedQuery) ||
      email.includes(normalizedQuery) ||
      phone.includes(normalizedQuery)
    );
  });
}

export const useMembersStore = create<MembersState>((set, get) => ({
  // Initial state
  members: [],
  filteredMembers: [],
  searchQuery: '',
  isLoading: false,
  isRefreshing: false,
  error: null,
  lastFetched: null,

  /**
   * Fetch members from API or cache
   * Requirements: 3.1, 3.8
   */
  fetchMembers: async (forceRefresh = false): Promise<void> => {
    const { lastFetched, searchQuery } = get();

    // Check if cache is still valid
    if (!forceRefresh && lastFetched) {
      const cacheAge = Date.now() - lastFetched;
      if (cacheAge < CACHE_DURATION.MEMBERS) {
        return;
      }
    }

    // Try to load from cache first
    if (!forceRefresh) {
      const cached = await storageService.get<CachedData<Member[]>>(
        STORAGE_KEYS.MEMBERS_CACHE
      );

      if (cached && Date.now() - cached.timestamp < CACHE_DURATION.MEMBERS) {
        const filtered = filterMembers(cached.data, searchQuery);
        set({
          members: cached.data,
          filteredMembers: filtered,
          lastFetched: cached.timestamp,
        });
        return;
      }
    }

    set({ isLoading: true, error: null });

    try {
      const response = await apiService.get<PaginatedResponse<Member>>('/members/');

      if (response.success) {
        const members = response.data.results;
        const filtered = filterMembers(members, searchQuery);

        // Cache the data
        await storageService.set(STORAGE_KEYS.MEMBERS_CACHE, {
          data: members,
          timestamp: Date.now(),
        });

        set({
          members,
          filteredMembers: filtered,
          isLoading: false,
          lastFetched: Date.now(),
        });
      } else {
        // Try to use cached data on error
        const cached = await storageService.get<CachedData<Member[]>>(
          STORAGE_KEYS.MEMBERS_CACHE
        );

        if (cached) {
          const filtered = filterMembers(cached.data, searchQuery);
          set({
            members: cached.data,
            filteredMembers: filtered,
            isLoading: false,
            error: 'Données hors ligne - dernière mise à jour: ' + 
              new Date(cached.timestamp).toLocaleString(),
          });
        } else {
          set({
            isLoading: false,
            error: response.error ?? 'Erreur lors du chargement des membres',
          });
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      
      // Try to use cached data on error
      const cached = await storageService.get<CachedData<Member[]>>(
        STORAGE_KEYS.MEMBERS_CACHE
      );

      if (cached) {
        const filtered = filterMembers(cached.data, searchQuery);
        set({
          members: cached.data,
          filteredMembers: filtered,
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
   * Set search query and filter members
   * Requirements: 3.2
   */
  setSearchQuery: (query: string): void => {
    const { members } = get();
    const filtered = filterMembers(members, query);
    set({
      searchQuery: query,
      filteredMembers: filtered,
    });
  },

  /**
   * Get a member by ID
   */
  getMemberById: (id: number): Member | undefined => {
    const { members } = get();
    return members.find((m) => m.id === id);
  },

  /**
   * Refresh members (pull-to-refresh)
   */
  refreshMembers: async (): Promise<void> => {
    set({ isRefreshing: true });
    await get().fetchMembers(true);
    set({ isRefreshing: false });
  },

  /**
   * Clear cached members data
   */
  clearCache: async (): Promise<void> => {
    await storageService.delete(STORAGE_KEYS.MEMBERS_CACHE);
    set({
      members: [],
      filteredMembers: [],
      lastFetched: null,
    });
  },
}));
