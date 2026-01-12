/**
 * Worship-related type definitions
 */

import type { Site } from './models';

export interface MemberSummary {
  id: number;
  firstName: string;
  lastName: string;
  photo?: string;
}

export interface ServiceRole {
  id: number;
  name: string;
  category: 'music' | 'tech' | 'liturgy';
}

export interface ServiceAssignment {
  id: number;
  role: ServiceRole;
  member: MemberSummary;
  status: 'pending' | 'confirmed' | 'declined';
  isCurrentUser: boolean;
}

export interface Song {
  id: number;
  title: string;
  author?: string;
  key?: string;
  order: number;
}

export interface WorshipService {
  id: number;
  date: string;
  serviceType: string;
  theme?: string;
  preacher?: string;
  status: 'planned' | 'confirmed' | 'completed';
  assignments: ServiceAssignment[];
  songs: Song[];
  site: Site;
}
