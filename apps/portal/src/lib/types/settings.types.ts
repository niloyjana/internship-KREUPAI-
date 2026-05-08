/**
 * Types for tenant settings, team management, and notification preferences.
 */

export interface TenantDetails {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
  countryCode: string;
  timezone: string;
  config: any;
  createdAt: string;
}

export interface UpdateTenantPayload {
  name?: string;
  countryCode?: string;
  timezone?: string;
}

export interface TeamUser {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string | null;
  status: string;
  lastLoginAt: string | null;
  createdAt: string;
}

export interface InviteUserPayload {
  email: string;
  name: string;
  role: string;
  department?: string;
}

export interface UpdateUserPayload {
  role?: string;
  department?: string;
}

export interface TeamUsersResponse {
  users: TeamUser[];
  meta: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  };
}

export interface NotificationPref {
  id: string;
  eventType: string;
  channels: string[];
  enabled: boolean;
}
