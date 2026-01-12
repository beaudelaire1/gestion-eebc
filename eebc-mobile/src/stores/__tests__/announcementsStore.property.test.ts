/**
 * AnnouncementsStore Property-Based Tests
 * Feature: eebc-mobile-app
 * Property 9: Announcement Sorting
 * Property 10: Read Status Tracking
 * Validates: Requirements 6.2, 6.4, 6.5
 *
 * Property 9: Announcement Sorting
 * For any list of announcements, pinned announcements SHALL appear before non-pinned,
 * and within each group, announcements SHALL be sorted by date descending.
 *
 * Property 10: Read Status Tracking
 * For any announcement viewed by a user, the announcement's isRead status SHALL be
 * set to true and persist across sessions.
 */

import fc from 'fast-check';
import {
  sortAnnouncements,
  calculateUnreadCount,
  applyReadStatus,
} from '../announcementsStore';
import type { Announcement } from '../../types/announcements';
import type { Site } from '../../types/models';

// Helper to create a valid Site
const createSite = (id: number = 1): Site => ({
  id,
  name: 'Test Site',
});

// Arbitrary for generating valid Announcement objects
const announcementArbitrary = fc
  .record({
    id: fc.integer({ min: 1, max: 10000 }),
    title: fc.string({ minLength: 1, maxLength: 100 }),
    content: fc.string({ minLength: 1, maxLength: 1000 }),
    excerpt: fc.string({ minLength: 1, maxLength: 200 }),
    imageUrl: fc.option(fc.webUrl(), { nil: undefined }),
    isPinned: fc.boolean(),
    publishedAt: fc.date({ min: new Date('2024-01-01'), max: new Date('2026-12-31') }),
    expiresAt: fc.option(
      fc.date({ min: new Date('2024-01-01'), max: new Date('2027-12-31') }),
      { nil: undefined }
    ),
    author: fc.string({ minLength: 1, maxLength: 50 }),
    isRead: fc.boolean(),
  })
  .map((data) => ({
    id: data.id,
    title: data.title,
    content: data.content,
    excerpt: data.excerpt,
    imageUrl: data.imageUrl,
    isPinned: data.isPinned,
    publishedAt: data.publishedAt.toISOString(),
    expiresAt: data.expiresAt?.toISOString(),
    author: data.author,
    isRead: data.isRead,
    site: createSite(),
  })) as fc.Arbitrary<Announcement>;

// Helper to check if array is sorted by date descending
function isSortedByDateDescending(announcements: Announcement[]): boolean {
  for (let i = 1; i < announcements.length; i++) {
    const prevDate = new Date(announcements[i - 1].publishedAt).getTime();
    const currDate = new Date(announcements[i].publishedAt).getTime();
    if (currDate > prevDate) {
      return false;
    }
  }
  return true;
}

describe('AnnouncementsStore Property Tests', () => {
  /**
   * Property 9: Announcement Sorting
   * Pinned announcements SHALL appear before non-pinned,
   * and within each group, sorted by date descending.
   */
  describe('Property 9: Announcement Sorting', () => {
    it('pinned announcements should appear before non-pinned', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 0, maxLength: 50 }),
          (announcements: Announcement[]) => {
            const sorted = sortAnnouncements(announcements);

            // Find the index where pinned announcements end
            let lastPinnedIndex = -1;
            let firstUnpinnedIndex = sorted.length;

            for (let i = 0; i < sorted.length; i++) {
              if (sorted[i].isPinned) {
                lastPinnedIndex = i;
              } else if (firstUnpinnedIndex === sorted.length) {
                firstUnpinnedIndex = i;
              }
            }

            // All pinned should come before all unpinned
            // This means lastPinnedIndex < firstUnpinnedIndex (or no pinned/unpinned exist)
            return lastPinnedIndex < firstUnpinnedIndex;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('pinned announcements should be sorted by date descending', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 0, maxLength: 50 }),
          (announcements: Announcement[]) => {
            const sorted = sortAnnouncements(announcements);
            const pinnedAnnouncements = sorted.filter((a) => a.isPinned);

            return isSortedByDateDescending(pinnedAnnouncements);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('non-pinned announcements should be sorted by date descending', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 0, maxLength: 50 }),
          (announcements: Announcement[]) => {
            const sorted = sortAnnouncements(announcements);
            const unpinnedAnnouncements = sorted.filter((a) => !a.isPinned);

            return isSortedByDateDescending(unpinnedAnnouncements);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('sorting should be idempotent', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 0, maxLength: 50 }),
          (announcements: Announcement[]) => {
            const firstSort = sortAnnouncements(announcements);
            const secondSort = sortAnnouncements(firstSort);

            // Sorting twice should give same results
            return (
              firstSort.length === secondSort.length &&
              firstSort.every((a, i) => a.id === secondSort[i].id)
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('sorting should preserve all announcements', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 0, maxLength: 50 }),
          (announcements: Announcement[]) => {
            const sorted = sortAnnouncements(announcements);

            // Same length
            if (sorted.length !== announcements.length) return false;

            // All original IDs should be present
            const originalIds = new Set(announcements.map((a) => a.id));
            const sortedIds = new Set(sorted.map((a) => a.id));

            return (
              originalIds.size === sortedIds.size &&
              [...originalIds].every((id) => sortedIds.has(id))
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Property 10: Read Status Tracking
   * For any announcement viewed, isRead status SHALL be set to true.
   */
  describe('Property 10: Read Status Tracking', () => {
    it('applying read status should mark announcements as read', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 1, maxLength: 50 }),
          fc.array(fc.integer({ min: 1, max: 10000 }), { minLength: 0, maxLength: 20 }),
          (announcements: Announcement[], readIds: number[]) => {
            // Create read status map
            const readStatus: { [id: number]: boolean } = {};
            readIds.forEach((id) => {
              readStatus[id] = true;
            });

            const result = applyReadStatus(announcements, readStatus);

            // All announcements with IDs in readStatus should be marked as read
            return result.every((announcement) => {
              if (readStatus[announcement.id]) {
                return announcement.isRead === true;
              }
              // Original isRead status should be preserved if not in readStatus
              const original = announcements.find((a) => a.id === announcement.id);
              return announcement.isRead === original?.isRead;
            });
          }
        ),
        { numRuns: 100 }
      );
    });

    it('unread count should decrease when announcements are marked as read', () => {
      fc.assert(
        fc.property(
          // Generate announcements that are all unread initially
          fc.array(
            announcementArbitrary.map((a) => ({ ...a, isRead: false })),
            { minLength: 1, maxLength: 30 }
          ),
          fc.nat({ max: 29 }),
          (announcements: Announcement[], numToRead: number) => {
            // Initial unread count
            const initialUnread = calculateUnreadCount(announcements, {});

            // Mark some as read
            const readStatus: { [id: number]: boolean } = {};
            const toMark = Math.min(numToRead, announcements.length);
            for (let i = 0; i < toMark; i++) {
              readStatus[announcements[i].id] = true;
            }

            const updatedAnnouncements = applyReadStatus(announcements, readStatus);
            const newUnread = calculateUnreadCount(updatedAnnouncements, readStatus);

            // Unread count should decrease by the number marked as read
            return newUnread === initialUnread - toMark;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('read status should be preserved when applied multiple times', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 1, maxLength: 30 }),
          fc.array(fc.integer({ min: 1, max: 10000 }), { minLength: 0, maxLength: 15 }),
          (announcements: Announcement[], readIds: number[]) => {
            const readStatus: { [id: number]: boolean } = {};
            readIds.forEach((id) => {
              readStatus[id] = true;
            });

            // Apply read status twice
            const firstApply = applyReadStatus(announcements, readStatus);
            const secondApply = applyReadStatus(firstApply, readStatus);

            // Results should be identical
            return firstApply.every((a, i) => a.isRead === secondApply[i].isRead);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('marking as read should be idempotent for unread count', () => {
      fc.assert(
        fc.property(
          fc.array(announcementArbitrary, { minLength: 1, maxLength: 30 }),
          fc.array(fc.integer({ min: 1, max: 10000 }), { minLength: 0, maxLength: 15 }),
          (announcements: Announcement[], readIds: number[]) => {
            const readStatus: { [id: number]: boolean } = {};
            readIds.forEach((id) => {
              readStatus[id] = true;
            });

            const applied = applyReadStatus(announcements, readStatus);
            const count1 = calculateUnreadCount(applied, readStatus);
            const count2 = calculateUnreadCount(applied, readStatus);

            // Unread count should be the same
            return count1 === count2;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
