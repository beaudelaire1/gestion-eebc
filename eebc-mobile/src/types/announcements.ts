/**
 * Announcement-related type definitions
 */

import type { Site } from './models';

export interface Announcement {
  id: number;
  title: string;
  content: string;
  excerpt: string;
  imageUrl?: string;
  isPinned: boolean;
  publishedAt: string;
  expiresAt?: string;
  author: string;
  isRead: boolean;
  site: Site;
}
