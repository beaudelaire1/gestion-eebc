/**
 * API-related type definitions
 */

export interface ApiResponse<T> {
  data: T;
  status: number;
  success: boolean;
  error?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuthResult {
  success: boolean;
  user?: User;
  accessToken?: string;
  refreshToken?: string;
  mustChangePassword?: boolean;
  error?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  memberId?: number;
  permissions: string[];
}

export type UserRole = 'admin' | 'pastor' | 'secretary' | 'leader' | 'member';

export interface QueuedAction {
  id: string;
  type: 'event_register' | 'worship_confirm' | 'profile_update';
  endpoint: string;
  method: 'POST' | 'PUT' | 'DELETE';
  data: Record<string, unknown>;
  createdAt: Date;
  retryCount: number;
}

export interface SyncResult {
  success: boolean;
  synced: number;
  failed: number;
  conflicts: SyncConflict[];
}

export interface SyncConflict {
  id: string;
  type: string;
  localData: Record<string, unknown>;
  serverData: Record<string, unknown>;
}
