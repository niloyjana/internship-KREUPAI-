export interface TenantProvisionedPayload {
  tenantId: string;
  name: string;
  slug: string;
  plan: 'STARTER' | 'GROWTH' | 'ENTERPRISE' | 'CUSTOM';
  adminUserId: string;
  adminEmail: string;
  countryCode: string;
  timezone: string;
}

export interface TenantStatusChangedPayload {
  tenantId: string;
  previousStatus: string;
  newStatus: string;
  reason: string;
  changedByUserId: string;
}

export interface TenantConfigUpdatedPayload {
  tenantId: string;
  agentId: string | null;
  configSection: 'policy' | 'integration' | 'branding' | string;
  changedKeys: string[];
  changedByUserId: string;
}

/** Non-spec extension — plan upgrade/downgrade events */
export interface TenantPlanChangedPayload {
  tenantId: string;
  previousPlan: string;
  newPlan: string;
  action: 'UPGRADE' | 'DOWNGRADE';
}
