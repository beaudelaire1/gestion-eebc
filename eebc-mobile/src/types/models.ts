/**
 * Data model type definitions
 */

export interface Site {
  id: number;
  name: string;
}

export interface Member {
  id: number;
  memberId: string;
  firstName: string;
  lastName: string;
  email?: string;
  phone?: string;
  whatsappNumber?: string;
  photo?: string;
  dateOfBirth?: string;
  gender: 'M' | 'F';
  maritalStatus: string;
  address?: string;
  city?: string;
  postalCode?: string;
  isBaptized: boolean;
  baptismDate?: string;
  status: 'active' | 'inactive' | 'visitor';
  family?: FamilyInfo;
  site: Site;
}

export interface FamilyInfo {
  id: number;
  name: string;
  role: 'head' | 'spouse' | 'child' | 'other';
  members: FamilyMember[];
}

export interface FamilyMember {
  id: number;
  firstName: string;
  lastName: string;
  relationship: string;
}

export interface Event {
  id: number;
  title: string;
  description: string;
  eventType: string;
  startDate: string;
  endDate: string;
  location?: string;
  isRecurring: boolean;
  maxParticipants?: number;
  currentParticipants: number;
  allowsRegistration: boolean;
  isUserRegistered: boolean;
  site: Site;
}

export interface EventRegistration {
  id: number;
  eventId: number;
  memberId: number;
  status: 'registered' | 'cancelled' | 'attended';
  registeredAt: string;
}
