import { apiClient } from './client';
import { useAuthStore } from '../stores/auth.store';
import type {
  TenantDetails,
  UpdateTenantPayload,
  TeamUser,
  TeamUsersResponse,
  InviteUserPayload,
  UpdateUserPayload,
  NotificationPref,
} from '../types/settings.types';

function getTenantId(): string {
  const user = useAuthStore.getState().user;
  if (!user?.tenantId) {
    throw new Error('No tenantId found in auth store');
  }
  return user.tenantId;
}

/**
 * Fetch the current tenant's details.
 */
export async function getTenantDetails(): Promise<TenantDetails> {
  const tenantId = getTenantId();
  const { data } = await apiClient.get<TenantDetails>(`/v1/tenants/${tenantId}`);
  return data;
}

/**
 * Update tenant details (name, countryCode, timezone).
 */
export async function updateTenant(payload: UpdateTenantPayload): Promise<TenantDetails> {
  const tenantId = getTenantId();
  const { data } = await apiClient.patch<TenantDetails>(`/v1/tenants/${tenantId}`, payload);
  return data;
}

/**
 * Fetch team users for the current tenant with pagination.
 */
export async function getTeamUsers(params?: {
  page?: number;
  pageSize?: number;
}): Promise<TeamUsersResponse> {
  const tenantId = getTenantId();
  const { data } = await apiClient.get<TeamUsersResponse>(`/v1/tenants/${tenantId}/users`, {
    params,
  });
  return data;
}

/**
 * Invite a new user to the tenant.
 */
export async function inviteUser(payload: InviteUserPayload): Promise<TeamUser> {
  const tenantId = getTenantId();
  const { data } = await apiClient.post<TeamUser>(`/v1/tenants/${tenantId}/users`, payload);
  return data;
}

/**
 * Update a user's role or department.
 */
export async function updateUser(userId: string, payload: UpdateUserPayload): Promise<TeamUser> {
  const tenantId = getTenantId();
  const { data } = await apiClient.patch<TeamUser>(
    `/v1/tenants/${tenantId}/users/${userId}`,
    payload,
  );
  return data;
}

/**
 * Remove a user from the tenant.
 */
export async function removeUser(userId: string): Promise<void> {
  const tenantId = getTenantId();
  await apiClient.delete(`/v1/tenants/${tenantId}/users/${userId}`);
}

/**
 * Fetch notification preferences for the current user.
 */
export async function getNotificationPreferences(): Promise<NotificationPref[]> {
  const { data } = await apiClient.get<NotificationPref[]>('/v1/notifications/preferences');
  return data;
}

/**
 * Update notification preferences.
 */
export async function updateNotificationPreferences(
  preferences: NotificationPref[],
): Promise<NotificationPref[]> {
  const { data } = await apiClient.put<NotificationPref[]>(
    '/v1/notifications/preferences',
    { preferences },
  );
  return data;
}
