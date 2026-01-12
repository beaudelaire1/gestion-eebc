/**
 * Donation-related type definitions
 */

export interface Donation {
  id: number;
  amount: number;
  currency: string;
  donationType: 'tithe' | 'offering' | 'special';
  fundName?: string;
  date: string;
  status: 'pending' | 'completed' | 'failed';
  receiptUrl?: string;
  isRecurring: boolean;
}

export interface DonationRequest {
  amount: number;
  donationType: string;
  fundId?: number;
  isRecurring: boolean;
  recurringInterval?: 'weekly' | 'monthly';
}
