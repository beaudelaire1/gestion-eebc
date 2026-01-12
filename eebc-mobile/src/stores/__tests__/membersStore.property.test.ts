/**
 * MembersStore Property-Based Tests
 * Feature: eebc-mobile-app, Property 7: Member Search Filtering
 * Validates: Requirements 3.2
 *
 * Property 7: Member Search Filtering
 * For any search query in the member directory, all returned results SHALL contain
 * the search term in either name, phone, or email fields.
 */

import fc from 'fast-check';
import { filterMembers } from '../membersStore';
import type { Member, Site } from '../../types/models';

// Helper to create a valid Site
const createSite = (id: number = 1): Site => ({
  id,
  name: 'Test Site',
});

// Arbitrary for generating valid Member objects
const memberArbitrary = fc.record({
  id: fc.integer({ min: 1, max: 10000 }),
  memberId: fc.string({ minLength: 1, maxLength: 20 }),
  firstName: fc.string({ minLength: 1, maxLength: 50 }),
  lastName: fc.string({ minLength: 1, maxLength: 50 }),
  email: fc.option(fc.emailAddress(), { nil: undefined }),
  phone: fc.option(
    fc.stringOf(fc.constantFrom('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '-', '+'), {
      minLength: 8,
      maxLength: 15,
    }),
    { nil: undefined }
  ),
  whatsappNumber: fc.option(fc.string({ minLength: 8, maxLength: 15 }), { nil: undefined }),
  photo: fc.option(fc.webUrl(), { nil: undefined }),
  dateOfBirth: fc.option(
    fc.date({ min: new Date('1920-01-01'), max: new Date('2010-01-01') }).map((d: Date) => d.toISOString().split('T')[0]),
    { nil: undefined }
  ),
  gender: fc.constantFrom('M', 'F') as fc.Arbitrary<'M' | 'F'>,
  maritalStatus: fc.constantFrom('single', 'married', 'widowed', 'divorced'),
  address: fc.option(fc.string({ minLength: 5, maxLength: 100 }), { nil: undefined }),
  city: fc.option(fc.string({ minLength: 2, maxLength: 50 }), { nil: undefined }),
  postalCode: fc.option(fc.string({ minLength: 4, maxLength: 10 }), { nil: undefined }),
  isBaptized: fc.boolean(),
  baptismDate: fc.option(
    fc.date({ min: new Date('1950-01-01'), max: new Date() }).map((d: Date) => d.toISOString().split('T')[0]),
    { nil: undefined }
  ),
  status: fc.constantFrom('active', 'inactive', 'visitor') as fc.Arbitrary<'active' | 'inactive' | 'visitor'>,
  family: fc.constant(undefined),
  site: fc.constant(createSite()),
});

describe('MembersStore Property Tests', () => {
  /**
   * Property 7: Member Search Filtering
   * For any search query, all returned results SHALL contain the search term
   * in either firstName, lastName, email, or phone fields.
   */
  describe('Property 7: Member Search Filtering', () => {
    it('all filtered results should contain the search query in name, email, or phone', () => {
      fc.assert(
        fc.property(
          fc.array(memberArbitrary, { minLength: 0, maxLength: 50 }),
          fc.string({ minLength: 1, maxLength: 20 }).filter((s: string) => s.trim().length > 0),
          (members: Member[], query: string) => {
            const results = filterMembers(members, query);
            const normalizedQuery = query.toLowerCase().trim();

            // Every result must contain the query in at least one searchable field
            return results.every((member) => {
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
        ),
        { numRuns: 100 }
      );
    });

    it('empty query should return all members', () => {
      fc.assert(
        fc.property(
          fc.array(memberArbitrary, { minLength: 0, maxLength: 50 }),
          fc.constantFrom('', '   ', '\t', '\n'),
          (members: Member[], emptyQuery: string) => {
            const results = filterMembers(members, emptyQuery);
            return results.length === members.length;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtering should be case-insensitive', () => {
      fc.assert(
        fc.property(
          fc.array(memberArbitrary, { minLength: 1, maxLength: 20 }),
          fc.nat({ max: 19 }),
          (members: Member[], index: number) => {
            // Pick a member and use part of their name as query
            const memberIndex = index % members.length;
            const member = members[memberIndex];
            const query = member.firstName.substring(0, Math.max(1, member.firstName.length / 2));

            if (query.trim().length === 0) return true;

            // Test with different cases
            const lowerResults = filterMembers(members, query.toLowerCase());
            const upperResults = filterMembers(members, query.toUpperCase());
            const mixedResults = filterMembers(members, query);

            // All should return the same results
            return (
              lowerResults.length === upperResults.length &&
              upperResults.length === mixedResults.length
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtered results should be a subset of original members', () => {
      fc.assert(
        fc.property(
          fc.array(memberArbitrary, { minLength: 0, maxLength: 50 }),
          fc.string({ minLength: 0, maxLength: 20 }),
          (members: Member[], query: string) => {
            const results = filterMembers(members, query);

            // Results count should never exceed original count
            if (results.length > members.length) return false;

            // Every result should exist in original array
            return results.every((result) =>
              members.some((m: Member) => m.id === result.id)
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtering should be idempotent', () => {
      fc.assert(
        fc.property(
          fc.array(memberArbitrary, { minLength: 0, maxLength: 50 }),
          fc.string({ minLength: 1, maxLength: 20 }).filter((s: string) => s.trim().length > 0),
          (members: Member[], query: string) => {
            const firstFilter = filterMembers(members, query);
            const secondFilter = filterMembers(firstFilter, query);

            // Filtering twice with same query should give same results
            return (
              firstFilter.length === secondFilter.length &&
              firstFilter.every((m, i) => m.id === secondFilter[i].id)
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
