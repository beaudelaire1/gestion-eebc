/**
 * Member Authorization Property-Based Tests
 * Feature: eebc-mobile-app, Property 8: Authorization Enforcement
 * Validates: Requirements 3.7
 *
 * Property 8: Authorization Enforcement
 * For any member data request, the response SHALL only include fields the requesting
 * user is authorized to view based on their role and privacy settings.
 */

import fc from 'fast-check';
import type { Member, Site } from '../../types/models';
import type { UserRole } from '../../types/api';

// Define which fields are visible to each role
interface FieldVisibility {
  public: (keyof Member)[];
  member: (keyof Member)[];
  leader: (keyof Member)[];
  secretary: (keyof Member)[];
  pastor: (keyof Member)[];
  admin: (keyof Member)[];
}

// Field visibility configuration based on role hierarchy
const FIELD_VISIBILITY: FieldVisibility = {
  // Public fields visible to all authenticated users
  public: ['id', 'firstName', 'lastName', 'photo', 'site'],
  // Additional fields visible to members
  member: ['id', 'firstName', 'lastName', 'photo', 'site', 'phone', 'email'],
  // Additional fields visible to leaders
  leader: ['id', 'firstName', 'lastName', 'photo', 'site', 'phone', 'email', 'whatsappNumber', 'status'],
  // Additional fields visible to secretaries
  secretary: [
    'id', 'firstName', 'lastName', 'photo', 'site', 'phone', 'email',
    'whatsappNumber', 'status', 'memberId', 'dateOfBirth', 'gender',
    'maritalStatus', 'address', 'city', 'postalCode', 'family'
  ],
  // Pastors can see everything except internal IDs
  pastor: [
    'id', 'firstName', 'lastName', 'photo', 'site', 'phone', 'email',
    'whatsappNumber', 'status', 'memberId', 'dateOfBirth', 'gender',
    'maritalStatus', 'address', 'city', 'postalCode', 'family',
    'isBaptized', 'baptismDate'
  ],
  // Admins can see all fields
  admin: [
    'id', 'memberId', 'firstName', 'lastName', 'email', 'phone',
    'whatsappNumber', 'photo', 'dateOfBirth', 'gender', 'maritalStatus',
    'address', 'city', 'postalCode', 'isBaptized', 'baptismDate',
    'status', 'family', 'site'
  ],
};

// All possible member fields
const ALL_MEMBER_FIELDS: (keyof Member)[] = [
  'id', 'memberId', 'firstName', 'lastName', 'email', 'phone',
  'whatsappNumber', 'photo', 'dateOfBirth', 'gender', 'maritalStatus',
  'address', 'city', 'postalCode', 'isBaptized', 'baptismDate',
  'status', 'family', 'site'
];

/**
 * Filter member data based on user role
 * This simulates what the API should return based on authorization
 */
export function filterMemberByRole(member: Member, role: UserRole): Partial<Member> {
  const allowedFields = FIELD_VISIBILITY[role] ?? FIELD_VISIBILITY.public;
  const filtered: Partial<Member> = {};

  for (const field of allowedFields) {
    if (field in member && member[field] !== undefined) {
      (filtered as Record<string, unknown>)[field] = member[field];
    }
  }

  return filtered;
}

/**
 * Check if a field is authorized for a given role
 */
export function isFieldAuthorized(field: keyof Member, role: UserRole): boolean {
  const allowedFields = FIELD_VISIBILITY[role] ?? FIELD_VISIBILITY.public;
  return allowedFields.includes(field);
}

/**
 * Get unauthorized fields for a role
 */
export function getUnauthorizedFields(role: UserRole): (keyof Member)[] {
  const allowedFields = FIELD_VISIBILITY[role] ?? FIELD_VISIBILITY.public;
  return ALL_MEMBER_FIELDS.filter(field => !allowedFields.includes(field));
}

// Helper to create a valid Site
const createSite = (id: number = 1): Site => ({
  id,
  name: 'Test Site',
});

// Arbitrary for generating valid Member objects
const memberArbitrary: fc.Arbitrary<Member> = fc.record({
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

// Arbitrary for user roles
const roleArbitrary: fc.Arbitrary<UserRole> = fc.constantFrom(
  'admin', 'pastor', 'secretary', 'leader', 'member'
);

describe('Member Authorization Property Tests', () => {
  /**
   * Property 8: Authorization Enforcement
   * For any member data request, the response SHALL only include fields
   * the requesting user is authorized to view based on their role.
   */
  describe('Property 8: Authorization Enforcement', () => {
    it('filtered member data should only contain authorized fields for the role', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          roleArbitrary,
          (member: Member, role: UserRole) => {
            const filtered = filterMemberByRole(member, role);
            const allowedFields = FIELD_VISIBILITY[role] ?? FIELD_VISIBILITY.public;

            // Every field in the filtered result must be in the allowed list
            const filteredKeys = Object.keys(filtered) as (keyof Member)[];
            return filteredKeys.every(key => allowedFields.includes(key));
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtered member data should not contain unauthorized fields', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          roleArbitrary,
          (member: Member, role: UserRole) => {
            const filtered = filterMemberByRole(member, role);
            const unauthorizedFields = getUnauthorizedFields(role);

            // No unauthorized field should be present in the filtered result
            const filteredKeys = Object.keys(filtered) as (keyof Member)[];
            return filteredKeys.every(key => !unauthorizedFields.includes(key));
          }
        ),
        { numRuns: 100 }
      );
    });

    it('admin role should have access to all fields', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          (member: Member) => {
            const filtered = filterMemberByRole(member, 'admin');
            const filteredKeys = Object.keys(filtered) as (keyof Member)[];

            // Admin should see all fields that have values
            const memberKeys = Object.keys(member).filter(
              key => member[key as keyof Member] !== undefined
            ) as (keyof Member)[];

            return memberKeys.every(key => filteredKeys.includes(key));
          }
        ),
        { numRuns: 100 }
      );
    });

    it('role hierarchy should be respected (higher roles see more)', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          (member: Member) => {
            const memberFiltered = filterMemberByRole(member, 'member');
            const leaderFiltered = filterMemberByRole(member, 'leader');
            const secretaryFiltered = filterMemberByRole(member, 'secretary');
            const pastorFiltered = filterMemberByRole(member, 'pastor');
            const adminFiltered = filterMemberByRole(member, 'admin');

            // Higher roles should see at least as many fields as lower roles
            const memberCount = Object.keys(memberFiltered).length;
            const leaderCount = Object.keys(leaderFiltered).length;
            const secretaryCount = Object.keys(secretaryFiltered).length;
            const pastorCount = Object.keys(pastorFiltered).length;
            const adminCount = Object.keys(adminFiltered).length;

            return (
              memberCount <= leaderCount &&
              leaderCount <= secretaryCount &&
              secretaryCount <= pastorCount &&
              pastorCount <= adminCount
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('public fields should always be visible to all roles', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          roleArbitrary,
          (member: Member, role: UserRole) => {
            const filtered = filterMemberByRole(member, role);
            const publicFields = FIELD_VISIBILITY.public;

            // All public fields that exist in member should be in filtered result
            return publicFields.every(field => {
              if (member[field] === undefined) return true;
              return field in filtered;
            });
          }
        ),
        { numRuns: 100 }
      );
    });

    it('sensitive fields should be hidden from basic member role', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          (member: Member) => {
            const filtered = filterMemberByRole(member, 'member');
            const sensitiveFields: (keyof Member)[] = [
              'dateOfBirth', 'address', 'city', 'postalCode',
              'isBaptized', 'baptismDate', 'maritalStatus'
            ];

            // Sensitive fields should not be visible to basic members
            const filteredKeys = Object.keys(filtered) as (keyof Member)[];
            return sensitiveFields.every(field => !filteredKeys.includes(field));
          }
        ),
        { numRuns: 100 }
      );
    });

    it('filtering should be idempotent', () => {
      fc.assert(
        fc.property(
          memberArbitrary,
          roleArbitrary,
          (member: Member, role: UserRole) => {
            const firstFilter = filterMemberByRole(member, role);
            const secondFilter = filterMemberByRole(firstFilter as Member, role);

            // Filtering twice should give the same result
            const firstKeys = Object.keys(firstFilter).sort();
            const secondKeys = Object.keys(secondFilter).sort();

            return (
              firstKeys.length === secondKeys.length &&
              firstKeys.every((key, i) => key === secondKeys[i])
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
