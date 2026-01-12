/**
 * Events Store - Zustand store for events and calendar management
 * Requirements: 4.1, 4.2, 4.4, 4.5
 */

import { create } from 'zustand';
import { Event, EventRegistration } from '../types/models';
import { PaginatedResponse, ApiResponse } from '../types/api';
import { apiService } from '../services/ApiService';
import { storageService } from '../services/StorageService';
import { STORAGE_KEYS, CACHE_DURATION } from '../constants';

interface CachedData<T> {
  data: T;
  timestamp: number;
}

interface EventsState {
  // State
  events: Event[];
  filteredEvents: Event[];
  selectedDate: string | null;
  registrations: Map<number, EventRegistration>;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastFetched: number | null;

  // Actions
  fetchEvents: (forceRefresh?: boolean) => Promise<void>;
  setSelectedDate: (date: string | null) => void;
  getEventsForDate: (date: string) => Event[];
  registerForEvent: (eventId: number) => Promise<boolean>;
  cancelRegistration: (eventId: number) => Promise<boolean>;
  getEventById: (id: number) => Event | undefined;
  refreshEvents: () => Promise<void>;
  clearCache: () => Promise<void>;
}

/**
 * Filter events by date
 * Returns events that occur on the specified date
 * Requirements: 4.2
 */
export function filterEventsByDate(events: Event[], date: string): Event[] {
  if (!date) {
    return events;
  }

  const targetDate = new Date(date);
  targetDate.setHours(0, 0, 0, 0);
  const targetDateStr = targetDate.toISOString().split('T')[0];

  return events.filter((event) => {
    const eventStartDate = new Date(event.startDate);
    eventStartDate.setHours(0, 0, 0, 0);
    const eventStartStr = eventStartDate.toISOString().split('T')[0];

    const eventEndDate = new Date(event.endDate);
    eventEndDate.setHours(0, 0, 0, 0);
    const eventEndStr = eventEndDate.toISOString().split('T')[0];

    // Event occurs on the target date if:
    // - It starts on that date, OR
    // - It ends on that date, OR
    // - The target date is between start and end
    return (
      eventStartStr === targetDateStr ||
      eventEndStr === targetDateStr ||
      (targetDateStr > eventStartStr && targetDateStr < eventEndStr)
    );
  });
}

/**
 * Check if an event occurs on a specific date
 */
export function eventOccursOnDate(event: Event, date: string): boolean {
  const targetDate = new Date(date);
  targetDate.setHours(0, 0, 0, 0);
  const targetDateStr = targetDate.toISOString().split('T')[0];

  const eventStartDate = new Date(event.startDate);
  eventStartDate.setHours(0, 0, 0, 0);
  const eventStartStr = eventStartDate.toISOString().split('T')[0];

  const eventEndDate = new Date(event.endDate);
  eventEndDate.setHours(0, 0, 0, 0);
  const eventEndStr = eventEndDate.toISOString().split('T')[0];

  return (
    eventStartStr === targetDateStr ||
    eventEndStr === targetDateStr ||
    (targetDateStr > eventStartStr && targetDateStr < eventEndStr)
  );
}

export const useEventsStore = create<EventsState>((set, get) => ({
  // Initial state
  events: [],
  filteredEvents: [],
  selectedDate: null,
  registrations: new Map(),
  isLoading: false,
  isRefreshing: false,
  error: null,
  lastFetched: null,

  /**
   * Fetch events from API or cache
   * Requirements: 4.1
   */
  fetchEvents: async (forceRefresh = false): Promise<void> => {
    const { lastFetched, selectedDate } = get();

    // Check if cache is still valid
    if (!forceRefresh && lastFetched) {
      const cacheAge = Date.now() - lastFetched;
      if (cacheAge < CACHE_DURATION.EVENTS) {
        return;
      }
    }

    // Try to load from cache first
    if (!forceRefresh) {
      const cached = await storageService.get<CachedData<Event[]>>(
        STORAGE_KEYS.EVENTS_CACHE
      );

      if (cached && Date.now() - cached.timestamp < CACHE_DURATION.EVENTS) {
        const filtered = selectedDate
          ? filterEventsByDate(cached.data, selectedDate)
          : cached.data;
        set({
          events: cached.data,
          filteredEvents: filtered,
          lastFetched: cached.timestamp,
        });
        return;
      }
    }

    set({ isLoading: true, error: null });

    try {
      const response = await apiService.get<PaginatedResponse<Event>>('/events/');

      if (response.success) {
        const events = response.data.results;
        const filtered = selectedDate
          ? filterEventsByDate(events, selectedDate)
          : events;

        // Cache the data
        await storageService.set(STORAGE_KEYS.EVENTS_CACHE, {
          data: events,
          timestamp: Date.now(),
        });

        set({
          events,
          filteredEvents: filtered,
          isLoading: false,
          lastFetched: Date.now(),
        });
      } else {
        // Try to use cached data on error
        const cached = await storageService.get<CachedData<Event[]>>(
          STORAGE_KEYS.EVENTS_CACHE
        );

        if (cached) {
          const filtered = selectedDate
            ? filterEventsByDate(cached.data, selectedDate)
            : cached.data;
          set({
            events: cached.data,
            filteredEvents: filtered,
            isLoading: false,
            error: 'Données hors ligne',
          });
        } else {
          set({
            isLoading: false,
            error: response.error ?? 'Erreur lors du chargement des événements',
          });
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';

      // Try to use cached data on error
      const cached = await storageService.get<CachedData<Event[]>>(
        STORAGE_KEYS.EVENTS_CACHE
      );

      if (cached) {
        const filtered = selectedDate
          ? filterEventsByDate(cached.data, selectedDate)
          : cached.data;
        set({
          events: cached.data,
          filteredEvents: filtered,
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
   * Set selected date and filter events
   * Requirements: 4.2
   */
  setSelectedDate: (date: string | null): void => {
    const { events } = get();
    const filtered = date ? filterEventsByDate(events, date) : events;
    set({
      selectedDate: date,
      filteredEvents: filtered,
    });
  },

  /**
   * Get events for a specific date
   * Requirements: 4.2
   */
  getEventsForDate: (date: string): Event[] => {
    const { events } = get();
    return filterEventsByDate(events, date);
  },

  /**
   * Register for an event
   * Requirements: 4.4, 4.5
   */
  registerForEvent: async (eventId: number): Promise<boolean> => {
    set({ isLoading: true, error: null });

    try {
      const response = await apiService.post<EventRegistration>(
        `/events/${eventId}/register/`,
        {}
      );

      if (response.success) {
        const { events, registrations, selectedDate } = get();

        // Update the event's registration status
        const updatedEvents = events.map((event) =>
          event.id === eventId
            ? {
                ...event,
                isUserRegistered: true,
                currentParticipants: event.currentParticipants + 1,
              }
            : event
        );

        // Store the registration
        const newRegistrations = new Map(registrations);
        newRegistrations.set(eventId, response.data);

        const filtered = selectedDate
          ? filterEventsByDate(updatedEvents, selectedDate)
          : updatedEvents;

        set({
          events: updatedEvents,
          filteredEvents: filtered,
          registrations: newRegistrations,
          isLoading: false,
        });

        return true;
      } else {
        set({
          isLoading: false,
          error: response.error ?? 'Erreur lors de l\'inscription',
        });
        return false;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return false;
    }
  },

  /**
   * Cancel registration for an event
   */
  cancelRegistration: async (eventId: number): Promise<boolean> => {
    set({ isLoading: true, error: null });

    try {
      const response = await apiService.delete(`/events/${eventId}/register/`);

      if (response.success) {
        const { events, registrations, selectedDate } = get();

        // Update the event's registration status
        const updatedEvents = events.map((event) =>
          event.id === eventId
            ? {
                ...event,
                isUserRegistered: false,
                currentParticipants: Math.max(0, event.currentParticipants - 1),
              }
            : event
        );

        // Remove the registration
        const newRegistrations = new Map(registrations);
        newRegistrations.delete(eventId);

        const filtered = selectedDate
          ? filterEventsByDate(updatedEvents, selectedDate)
          : updatedEvents;

        set({
          events: updatedEvents,
          filteredEvents: filtered,
          registrations: newRegistrations,
          isLoading: false,
        });

        return true;
      } else {
        set({
          isLoading: false,
          error: response.error ?? 'Erreur lors de l\'annulation',
        });
        return false;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return false;
    }
  },

  /**
   * Get an event by ID
   */
  getEventById: (id: number): Event | undefined => {
    const { events } = get();
    return events.find((e) => e.id === id);
  },

  /**
   * Refresh events (pull-to-refresh)
   */
  refreshEvents: async (): Promise<void> => {
    set({ isRefreshing: true });
    await get().fetchEvents(true);
    set({ isRefreshing: false });
  },

  /**
   * Clear cached events data
   */
  clearCache: async (): Promise<void> => {
    await storageService.delete(STORAGE_KEYS.EVENTS_CACHE);
    set({
      events: [],
      filteredEvents: [],
      lastFetched: null,
    });
  },
}));
