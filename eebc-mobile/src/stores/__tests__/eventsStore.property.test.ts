/**
 * EventsStore Property-Based Tests
 * Feature: eebc-mobile-app, Property 6: Event Date Filtering
 * Validates: Requirements 4.2
 *
 * Property 6: Event Date Filtering
 * For any date selection in the calendar, the displayed events SHALL only include
 * events occurring on that specific date.
 */

import fc from 'fast-check';
import { filterEventsByDate, eventOccursOnDate } from '../eventsStore';
import type { Event, Site } from '../../types/models';

// Helper to create a valid Site
const createSite = (id: number = 1): Site => ({
  id,
  name: 'Test Site',
});

// Helper to format date as ISO string (date only)
const formatDate = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

// Arbitrary for generating valid Event objects
const eventArbitrary = fc
  .record({
    id: fc.integer({ min: 1, max: 10000 }),
    title: fc.string({ minLength: 1, maxLength: 100 }),
    description: fc.string({ minLength: 0, maxLength: 500 }),
    eventType: fc.constantFrom('worship', 'meeting', 'social', 'training', 'other'),
    startDate: fc.date({ min: new Date('2024-01-01'), max: new Date('2026-12-31') }),
    duration: fc.integer({ min: 0, max: 7 }), // Duration in days
    location: fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: undefined }),
    isRecurring: fc.boolean(),
    maxParticipants: fc.option(fc.integer({ min: 1, max: 1000 }), { nil: undefined }),
    currentParticipants: fc.integer({ min: 0, max: 100 }),
    allowsRegistration: fc.boolean(),
    isUserRegistered: fc.boolean(),
  })
  .map((data) => {
    const startDate = data.startDate;
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + data.duration);

    return {
      id: data.id,
      title: data.title,
      description: data.description,
      eventType: data.eventType,
      startDate: startDate.toISOString(),
      endDate: endDate.toISOString(),
      location: data.location,
      isRecurring: data.isRecurring,
      maxParticipants: data.maxParticipants,
      currentParticipants: data.currentParticipants,
      allowsRegistration: data.allowsRegistration,
      isUserRegistered: data.isUserRegistered,
      site: createSite(),
    } as Event;
  });

// Arbitrary for generating dates within a reasonable range
const dateArbitrary = fc
  .date({ min: new Date('2024-01-01'), max: new Date('2026-12-31') })
  .map((d: Date) => formatDate(d));

describe('EventsStore Property Tests', () => {
  /**
   * Property 6: Event Date Filtering
   * For any date selection, all returned events SHALL occur on that specific date.
   */
  describe('Property 6: Event Date Filtering', () => {
    it('all filtered events should occur on the selected date', () => {
      fc.assert(
        fc.property(
          fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
          dateArbitrary,
          (events: Event[], selectedDate: string) => {
            const results = filterEventsByDate(events, selectedDate);

            // Every result must occur on the selected date
            return results.every((event) => eventOccursOnDate(event, selectedDate));
          }
        ),
        { numRuns: 100 }
      );
    });

    it('events not occurring on the date should not be included', () => {
      fc.assert(
        fc.property(
          fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
          dateArbitrary,
          (events: Event[], selectedDate: string) => {
            const results = filterEventsByDate(events, selectedDate);
            const resultIds = new Set(results.map((e) => e.id));

            // Events not in results should NOT occur on the selected date
            const excludedEvents = events.filter((e) => !resultIds.has(e.id));
            return excludedEvents.every((event) => !eventOccursOnDate(event, selectedDate));
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtering should be idempotent', () => {
      fc.assert(
        fc.property(
          fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
          dateArbitrary,
          (events: Event[], selectedDate: string) => {
            const firstFilter = filterEventsByDate(events, selectedDate);
            const secondFilter = filterEventsByDate(firstFilter, selectedDate);

            // Filtering twice should give same results
            return (
              firstFilter.length === secondFilter.length &&
              firstFilter.every((e, i) => e.id === secondFilter[i].id)
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtered results should be a subset of original events', () => {
      fc.assert(
        fc.property(
          fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
          dateArbitrary,
          (events: Event[], selectedDate: string) => {
            const results = filterEventsByDate(events, selectedDate);

            // Results count should never exceed original count
            if (results.length > events.length) return false;

            // Every result should exist in original array
            return results.every((result) =>
              events.some((e: Event) => e.id === result.id)
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('event starting on selected date should be included', () => {
      fc.assert(
        fc.property(
          eventArbitrary,
          (event: Event) => {
            const startDate = formatDate(new Date(event.startDate));
            const results = filterEventsByDate([event], startDate);

            // Event should be included when filtering by its start date
            return results.length === 1 && results[0].id === event.id;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('event ending on selected date should be included', () => {
      fc.assert(
        fc.property(
          eventArbitrary,
          (event: Event) => {
            const endDate = formatDate(new Date(event.endDate));
            const results = filterEventsByDate([event], endDate);

            // Event should be included when filtering by its end date
            return results.length === 1 && results[0].id === event.id;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('multi-day event should be included for dates in between', () => {
      fc.assert(
        fc.property(
          // Generate events with duration > 1 day
          fc
            .record({
              id: fc.integer({ min: 1, max: 10000 }),
              title: fc.string({ minLength: 1, maxLength: 50 }),
              description: fc.string({ minLength: 0, maxLength: 100 }),
              eventType: fc.constant('meeting'),
              startDate: fc.date({ min: new Date('2024-01-01'), max: new Date('2026-06-01') }),
              duration: fc.integer({ min: 3, max: 10 }), // At least 3 days
            })
            .map((data) => {
              const startDate = data.startDate;
              const endDate = new Date(startDate);
              endDate.setDate(endDate.getDate() + data.duration);

              return {
                id: data.id,
                title: data.title,
                description: data.description,
                eventType: data.eventType,
                startDate: startDate.toISOString(),
                endDate: endDate.toISOString(),
                location: undefined,
                isRecurring: false,
                maxParticipants: undefined,
                currentParticipants: 0,
                allowsRegistration: true,
                isUserRegistered: false,
                site: createSite(),
              } as Event;
            }),
          (event: Event) => {
            // Pick a date in the middle of the event
            const startDate = new Date(event.startDate);
            const middleDate = new Date(startDate);
            middleDate.setDate(middleDate.getDate() + 1); // Day after start
            const middleDateStr = formatDate(middleDate);

            const results = filterEventsByDate([event], middleDateStr);

            // Event should be included for a date in the middle
            return results.length === 1 && results[0].id === event.id;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
