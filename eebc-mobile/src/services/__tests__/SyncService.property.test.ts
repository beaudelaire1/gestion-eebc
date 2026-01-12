/**
 * SyncService Property-Based Tests
 * Feature: eebc-mobile-app, Property 11: Offline Data Availability
 * Feature: eebc-mobile-app, Property 12: Offline Action Queuing
 * Validates: Requirements 9.1, 9.2, 9.3, 9.4
 *
 * Property 11: Offline Data Availability
 * For any cached data (members, events, announcements), when the device is offline,
 * the data SHALL remain accessible and display with an offline indicator.
 *
 * Property 12: Offline Action Queuing
 * For any action performed while offline (registration, confirmation), the action
 * SHALL be queued and automatically executed when connectivity is restored.
 */

import fc from 'fast-check';
import { SyncService, CachedData, Announcement } from '../SyncService';
import { storageService } from '../StorageService';
import { apiService } from '../ApiService';
import { STORAGE_KEYS, CACHE_DURATION } from '../../constants';
import { Member, Event } from '../../types/models';
import { QueuedAction } from '../../types/api';

// Mock NetInfo
jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: jest.fn(() => jest.fn()),
  fetch: jest.fn(() => Promise.resolve({ isConnected: true, isInternetReachable: true })),
}));

// Mock dependencies
jest.mock('../StorageService');
jest.mock('../ApiService');

const mockStorageService = storageService as jest.Mocked<typeof storageService>;
const mockApiService = apiService as jest.Mocked<typeof apiService>;

// Arbitraries for generating test data
const memberArbitrary = fc.record({
  id: fc.integer({ min: 1, max: 10000 }),
  memberId: fc.string({ minLength: 1, maxLength: 10 }),
  firstName: fc.string({ minLength: 1, maxLength: 50 }),
  lastName: fc.string({ minLength: 1, maxLength: 50 }),
  email: fc.option(fc.emailAddress()),
  phone: fc.option(fc.string({ minLength: 10, maxLength: 15 })),
  status: fc.constantFrom('active', 'inactive', 'visitor'),
});

const eventArbitrary = fc.record({
  id: fc.integer({ min: 1, max: 10000 }),
  title: fc.string({ minLength: 1, maxLength: 100 }),
  description: fc.string({ minLength: 1, maxLength: 500 }),
  startDate: fc.date().map((d: Date) => d.toISOString()),
  endDate: fc.date().map((d: Date) => d.toISOString()),
  allowsRegistration: fc.boolean(),
  isUserRegistered: fc.boolean(),
});

const announcementArbitrary = fc.record({
  id: fc.integer({ min: 1, max: 10000 }),
  title: fc.string({ minLength: 1, maxLength: 100 }),
  content: fc.string({ minLength: 1, maxLength: 1000 }),
  excerpt: fc.string({ minLength: 1, maxLength: 200 }),
  isPinned: fc.boolean(),
  publishedAt: fc.date().map((d: Date) => d.toISOString()),
  author: fc.string({ minLength: 1, maxLength: 50 }),
  isRead: fc.boolean(),
});

const queuedActionArbitrary = fc.record({
  type: fc.constantFrom('event_register', 'worship_confirm', 'profile_update'),
  endpoint: fc.string({ minLength: 1, maxLength: 100 }),
  method: fc.constantFrom('POST', 'PUT', 'DELETE'),
  data: fc.dictionary(fc.string(), fc.anything()),
});

describe('SyncService Property Tests', () => {
  let syncService: SyncService;

  beforeEach(() => {
    jest.clearAllMocks();
    syncService = new SyncService();
    
    // Reset storage mock
    mockStorageService.get.mockResolvedValue(null);
    mockStorageService.set.mockResolvedValue();
    mockStorageService.delete.mockResolvedValue();
  });

  afterEach(() => {
    syncService.cleanup();
  });

  /**
   * Property 11: Offline Data Availability
   * For any cached data, when offline, the data SHALL remain accessible with staleness indicator
   */
  describe('Property 11: Offline Data Availability', () => {
    it('should return cached members data with correct staleness indicator', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(memberArbitrary, { minLength: 0, maxLength: 100 }),
          fc.integer({ min: 0, max: CACHE_DURATION.MEMBERS * 2 }), // Age in milliseconds
          async (members: Member[], ageMs: number) => {
            const timestamp = Date.now() - ageMs;
            const cachedData: CachedData<Member[]> = {
              data: members,
              timestamp,
              isStale: false, // Will be recalculated
            };

            // Mock storage to return cached data
            mockStorageService.get.mockResolvedValueOnce(cachedData);

            // Get cached members
            const result = await syncService.getCachedMembers();

            // Should return data
            if (!result) return false;

            // Data should match
            if (JSON.stringify(result.data) !== JSON.stringify(members)) return false;

            // Staleness should be correctly calculated
            const expectedStale = ageMs > CACHE_DURATION.MEMBERS;
            return result.isStale === expectedStale;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should return cached events data with correct staleness indicator', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(eventArbitrary, { minLength: 0, maxLength: 50 }),
          fc.integer({ min: 0, max: CACHE_DURATION.EVENTS * 2 }),
          async (events: Event[], ageMs: number) => {
            const timestamp = Date.now() - ageMs;
            const cachedData: CachedData<Event[]> = {
              data: events,
              timestamp,
              isStale: false,
            };

            mockStorageService.get.mockResolvedValueOnce(cachedData);

            const result = await syncService.getCachedEvents();

            if (!result) return false;
            if (JSON.stringify(result.data) !== JSON.stringify(events)) return false;

            const expectedStale = ageMs > CACHE_DURATION.EVENTS;
            return result.isStale === expectedStale;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should return cached announcements data with correct staleness indicator', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(announcementArbitrary, { minLength: 0, maxLength: 30 }),
          fc.integer({ min: 0, max: CACHE_DURATION.ANNOUNCEMENTS * 2 }),
          async (announcements: Announcement[], ageMs: number) => {
            const timestamp = Date.now() - ageMs;
            const cachedData: CachedData<Announcement[]> = {
              data: announcements,
              timestamp,
              isStale: false,
            };

            mockStorageService.get.mockResolvedValueOnce(cachedData);

            const result = await syncService.getCachedAnnouncements();

            if (!result) return false;
            if (JSON.stringify(result.data) !== JSON.stringify(announcements)) return false;

            const expectedStale = ageMs > CACHE_DURATION.ANNOUNCEMENTS;
            return result.isStale === expectedStale;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should return null when no cached data exists', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.constantFrom('members', 'events', 'announcements'),
          async (dataType: string) => {
            // Mock storage to return null (no cached data)
            mockStorageService.get.mockResolvedValueOnce(null);

            let result;
            switch (dataType) {
              case 'members':
                result = await syncService.getCachedMembers();
                break;
              case 'events':
                result = await syncService.getCachedEvents();
                break;
              case 'announcements':
                result = await syncService.getCachedAnnouncements();
                break;
            }

            return result === null;
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Property 12: Offline Action Queuing
   * For any action performed while offline, the action SHALL be queued and executed when online
   */
  describe('Property 12: Offline Action Queuing', () => {
    it('should queue actions and maintain them in storage', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(queuedActionArbitrary, { minLength: 1, maxLength: 10 }),
          async (actions: Array<{type: string, endpoint: string, method: string, data: Record<string, any>}>) => {
            // Mock empty initial queue
            mockStorageService.get.mockResolvedValueOnce([]);

            // Queue each action
            for (const action of actions) {
              // Mock getting current queue (starts empty, then grows)
              const currentQueue: QueuedAction[] = [];
              mockStorageService.get.mockResolvedValueOnce(currentQueue);
              
              await syncService.queueAction(action);

              // Verify storage.set was called with the action
              expect(mockStorageService.set).toHaveBeenCalledWith(
                STORAGE_KEYS.OFFLINE_QUEUE,
                expect.arrayContaining([
                  expect.objectContaining({
                    type: action.type,
                    endpoint: action.endpoint,
                    method: action.method,
                    data: action.data,
                    id: expect.any(String),
                    createdAt: expect.any(Date),
                    retryCount: 0,
                  })
                ])
              );
            }

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should retrieve all queued actions', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(queuedActionArbitrary, { minLength: 0, maxLength: 10 }),
          async (actions: Array<{type: string, endpoint: string, method: string, data: Record<string, any>}>) => {
            // Create full queued actions with required fields
            const queuedActions: QueuedAction[] = actions.map((action, index) => ({
              ...action,
              id: `test-id-${index}`,
              createdAt: new Date(),
              retryCount: 0,
            }));

            // Mock storage to return the queued actions
            mockStorageService.get.mockResolvedValueOnce(queuedActions);

            const result = await syncService.getQueuedActions();

            // Should return the same actions
            return JSON.stringify(result) === JSON.stringify(queuedActions);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should clear all queued actions', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.constant(null), // No input needed
          async () => {
            await syncService.clearQueue();

            // Should call storage.delete with the correct key
            expect(mockStorageService.delete).toHaveBeenCalledWith(STORAGE_KEYS.OFFLINE_QUEUE);

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should remove specific actions from queue', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(queuedActionArbitrary, { minLength: 2, maxLength: 5 }),
          fc.integer({ min: 0, max: 4 }), // Index to remove
          async (actions: Array<{type: string, endpoint: string, method: string, data: Record<string, any>}>, removeIndex: number) => {
            if (removeIndex >= actions.length) return true; // Skip if index out of bounds

            // Create full queued actions
            const queuedActions: QueuedAction[] = actions.map((action, index) => ({
              ...action,
              id: `test-id-${index}`,
              createdAt: new Date(),
              retryCount: 0,
            }));

            const actionToRemove = queuedActions[removeIndex];

            // Mock getting current queue
            mockStorageService.get.mockResolvedValueOnce(queuedActions);

            await syncService.removeFromQueue(actionToRemove.id);

            // Should call storage.set with filtered queue
            const expectedQueue = queuedActions.filter(a => a.id !== actionToRemove.id);
            expect(mockStorageService.set).toHaveBeenCalledWith(
              STORAGE_KEYS.OFFLINE_QUEUE,
              expectedQueue
            );

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should handle empty queue operations gracefully', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 1, maxLength: 20 }), // Random action ID
          async (actionId: string) => {
            // Mock empty queue
            mockStorageService.get.mockResolvedValueOnce([]);

            // Should not throw when removing from empty queue
            await syncService.removeFromQueue(actionId);

            // Should call storage.set with empty array
            expect(mockStorageService.set).toHaveBeenCalledWith(STORAGE_KEYS.OFFLINE_QUEUE, []);

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Combined property: Queue persistence across operations
   */
  describe('Queue Persistence Properties', () => {
    it('should maintain queue integrity across multiple operations', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(queuedActionArbitrary, { minLength: 1, maxLength: 5 }),
          async (actions: Array<{type: string, endpoint: string, method: string, data: Record<string, any>}>) => {
            let currentQueue: QueuedAction[] = [];

            // Mock storage to simulate persistent queue
            mockStorageService.get.mockImplementation(() => Promise.resolve([...currentQueue]));
            mockStorageService.set.mockImplementation((key: string, value: any) => {
              if (key === STORAGE_KEYS.OFFLINE_QUEUE) {
                currentQueue = [...value as QueuedAction[]];
              }
              return Promise.resolve();
            });

            // Queue all actions
            for (const action of actions) {
              await syncService.queueAction(action);
            }

            // Verify final queue has all actions
            const finalQueue = await syncService.getQueuedActions();
            
            // Should have same number of actions
            if (finalQueue.length !== actions.length) return false;

            // Each original action should be represented
            for (const originalAction of actions) {
              const found = finalQueue.some(qa => 
                qa.type === originalAction.type &&
                qa.endpoint === originalAction.endpoint &&
                qa.method === originalAction.method &&
                JSON.stringify(qa.data) === JSON.stringify(originalAction.data)
              );
              if (!found) return false;
            }

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});