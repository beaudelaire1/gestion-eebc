/**
 * Worship Store - Zustand store for worship services and assignments management
 * Requirements: 5.1, 5.2, 5.4
 */

import { create } from 'zustand';
import { WorshipService, ServiceAssignment } from '../types/worship';
import { PaginatedResponse } from '../types/api';
import { apiService } from '../services/ApiService';
import { storageService } from '../services/StorageService';

const WORSHIP_CACHE_KEY = 'worship_services_cache';
const WORSHIP_CACHE_DURATION = 30 * 60 * 1000; // 30 minutes

interface CachedData<T> {
  data: T;
  timestamp: number;
}

interface ConfirmationResult {
  success: boolean;
  assignment?: ServiceAssignment;
  error?: string;
}

interface WorshipState {
  // State
  services: WorshipService[];
  myAssignments: ServiceAssignment[];
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastFetched: number | null;

  // Actions
  fetchServices: (forceRefresh?: boolean) => Promise<void>;
  fetchMyAssignments: () => Promise<void>;
  confirmAssignment: (assignmentId: number) => Promise<ConfirmationResult>;
  declineAssignment: (assignmentId: number, reason: string) => Promise<ConfirmationResult>;
  getServiceById: (id: number) => WorshipService | undefined;
  getUpcomingServices: () => WorshipService[];
  getMyUpcomingAssignments: () => ServiceAssignment[];
  refreshServices: () => Promise<void>;
  clearCache: () => Promise<void>;
}

/**
 * Get upcoming services (future services only)
 */
export function getUpcomingServicesFromList(services: WorshipService[]): WorshipService[] {
  const now = new Date();
  now.setHours(0, 0, 0, 0);

  return services
    .filter((service) => {
      const serviceDate = new Date(service.date);
      serviceDate.setHours(0, 0, 0, 0);
      return serviceDate >= now;
    })
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}

/**
 * Get user's assignments from services
 */
export function extractUserAssignments(services: WorshipService[]): ServiceAssignment[] {
  const assignments: ServiceAssignment[] = [];

  for (const service of services) {
    for (const assignment of service.assignments) {
      if (assignment.isCurrentUser) {
        assignments.push(assignment);
      }
    }
  }

  return assignments;
}

export const useWorshipStore = create<WorshipState>((set, get) => ({
  // Initial state
  services: [],
  myAssignments: [],
  isLoading: false,
  isRefreshing: false,
  error: null,
  lastFetched: null,

  /**
   * Fetch worship services from API or cache
   * Requirements: 5.1
   */
  fetchServices: async (forceRefresh = false): Promise<void> => {
    const { lastFetched } = get();

    // Check if cache is still valid
    if (!forceRefresh && lastFetched) {
      const cacheAge = Date.now() - lastFetched;
      if (cacheAge < WORSHIP_CACHE_DURATION) {
        return;
      }
    }

    // Try to load from cache first
    if (!forceRefresh) {
      const cached = await storageService.get<CachedData<WorshipService[]>>(
        WORSHIP_CACHE_KEY
      );

      if (cached && Date.now() - cached.timestamp < WORSHIP_CACHE_DURATION) {
        const myAssignments = extractUserAssignments(cached.data);
        set({
          services: cached.data,
          myAssignments,
          lastFetched: cached.timestamp,
        });
        return;
      }
    }

    set({ isLoading: true, error: null });

    try {
      const response = await apiService.get<PaginatedResponse<WorshipService>>(
        '/worship/services/'
      );

      if (response.success) {
        const services = response.data.results;
        const myAssignments = extractUserAssignments(services);

        // Cache the data
        await storageService.set(WORSHIP_CACHE_KEY, {
          data: services,
          timestamp: Date.now(),
        });

        set({
          services,
          myAssignments,
          isLoading: false,
          lastFetched: Date.now(),
        });
      } else {
        // Try to use cached data on error
        const cached = await storageService.get<CachedData<WorshipService[]>>(
          WORSHIP_CACHE_KEY
        );

        if (cached) {
          const myAssignments = extractUserAssignments(cached.data);
          set({
            services: cached.data,
            myAssignments,
            isLoading: false,
            error: 'Données hors ligne',
          });
        } else {
          set({
            isLoading: false,
            error: response.error ?? 'Erreur lors du chargement des services',
          });
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';

      // Try to use cached data on error
      const cached = await storageService.get<CachedData<WorshipService[]>>(
        WORSHIP_CACHE_KEY
      );

      if (cached) {
        const myAssignments = extractUserAssignments(cached.data);
        set({
          services: cached.data,
          myAssignments,
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
   * Fetch user's assignments
   * Requirements: 5.2
   */
  fetchMyAssignments: async (): Promise<void> => {
    // Assignments are extracted from services
    // This method ensures services are loaded first
    await get().fetchServices();
  },

  /**
   * Confirm an assignment
   * Requirements: 5.4
   */
  confirmAssignment: async (assignmentId: number): Promise<ConfirmationResult> => {
    set({ isLoading: true, error: null });

    try {
      const response = await apiService.post<ServiceAssignment>(
        '/worship/confirm/',
        {
          assignment_id: assignmentId,
          status: 'confirmed',
        }
      );

      if (response.success) {
        const { services } = get();

        // Update the assignment status in services
        const updatedServices = services.map((service) => ({
          ...service,
          assignments: service.assignments.map((assignment) =>
            assignment.id === assignmentId
              ? { ...assignment, status: 'confirmed' as const }
              : assignment
          ),
        }));

        const myAssignments = extractUserAssignments(updatedServices);

        // Update cache
        await storageService.set(WORSHIP_CACHE_KEY, {
          data: updatedServices,
          timestamp: Date.now(),
        });

        set({
          services: updatedServices,
          myAssignments,
          isLoading: false,
        });

        return {
          success: true,
          assignment: response.data,
        };
      } else {
        set({
          isLoading: false,
          error: response.error ?? 'Erreur lors de la confirmation',
        });
        return {
          success: false,
          error: response.error ?? 'Erreur lors de la confirmation',
        };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return {
        success: false,
        error: errorMessage,
      };
    }
  },

  /**
   * Decline an assignment
   * Requirements: 5.4, 5.5
   */
  declineAssignment: async (
    assignmentId: number,
    reason: string
  ): Promise<ConfirmationResult> => {
    set({ isLoading: true, error: null });

    try {
      const response = await apiService.post<ServiceAssignment>(
        '/worship/confirm/',
        {
          assignment_id: assignmentId,
          status: 'declined',
          reason,
        }
      );

      if (response.success) {
        const { services } = get();

        // Update the assignment status in services
        const updatedServices = services.map((service) => ({
          ...service,
          assignments: service.assignments.map((assignment) =>
            assignment.id === assignmentId
              ? { ...assignment, status: 'declined' as const }
              : assignment
          ),
        }));

        const myAssignments = extractUserAssignments(updatedServices);

        // Update cache
        await storageService.set(WORSHIP_CACHE_KEY, {
          data: updatedServices,
          timestamp: Date.now(),
        });

        set({
          services: updatedServices,
          myAssignments,
          isLoading: false,
        });

        return {
          success: true,
          assignment: response.data,
        };
      } else {
        set({
          isLoading: false,
          error: response.error ?? 'Erreur lors du refus',
        });
        return {
          success: false,
          error: response.error ?? 'Erreur lors du refus',
        };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return {
        success: false,
        error: errorMessage,
      };
    }
  },

  /**
   * Get a service by ID
   */
  getServiceById: (id: number): WorshipService | undefined => {
    const { services } = get();
    return services.find((s) => s.id === id);
  },

  /**
   * Get upcoming services
   */
  getUpcomingServices: (): WorshipService[] => {
    const { services } = get();
    return getUpcomingServicesFromList(services);
  },

  /**
   * Get user's upcoming assignments
   */
  getMyUpcomingAssignments: (): ServiceAssignment[] => {
    const { services } = get();
    const upcomingServices = getUpcomingServicesFromList(services);
    return extractUserAssignments(upcomingServices);
  },

  /**
   * Refresh services (pull-to-refresh)
   */
  refreshServices: async (): Promise<void> => {
    set({ isRefreshing: true });
    await get().fetchServices(true);
    set({ isRefreshing: false });
  },

  /**
   * Clear cached services data
   */
  clearCache: async (): Promise<void> => {
    await storageService.delete(WORSHIP_CACHE_KEY);
    set({
      services: [],
      myAssignments: [],
      lastFetched: null,
    });
  },
}));
