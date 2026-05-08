// ──────────────────────────────────────────────────────────────
// HubSpot connector request / response interfaces
// ──────────────────────────────────────────────────────────────

/** Common pagination parameters for HubSpot list endpoints. */
export interface HubSpotListParams {
  /** Maximum results to return (default 10, max 100). */
  limit?: number;
  /** Cursor for forward pagination. */
  after?: string;
  /** Comma-separated list of properties to include. */
  properties?: string[];
}

/** HubSpot paging cursor. */
export interface HubSpotPaging {
  next?: { after: string; link: string };
}

// ── Contacts ────────────────────────────────────────────────

export interface HubSpotContactProperties {
  email?: string;
  firstname?: string;
  lastname?: string;
  phone?: string;
  company?: string;
  jobtitle?: string;
  [key: string]: string | undefined;
}

export interface HubSpotContact {
  id: string;
  properties: HubSpotContactProperties;
  createdAt: string;
  updatedAt: string;
  archived: boolean;
}

export interface ListContactsResult {
  results: HubSpotContact[];
  paging?: HubSpotPaging;
  total: number;
}

export interface CreateContactData {
  email: string;
  firstname?: string;
  lastname?: string;
  phone?: string;
  company?: string;
  jobtitle?: string;
  [key: string]: string | undefined;
}

// ── Deals ────────────────────────────────────────────────────

export interface HubSpotDealProperties {
  dealname?: string;
  amount?: string;
  dealstage?: string;
  pipeline?: string;
  closedate?: string;
  [key: string]: string | undefined;
}

export interface HubSpotDeal {
  id: string;
  properties: HubSpotDealProperties;
  createdAt: string;
  updatedAt: string;
  archived: boolean;
}

export interface ListDealsResult {
  results: HubSpotDeal[];
  paging?: HubSpotPaging;
  total: number;
}

export interface CreateDealData {
  dealname: string;
  amount?: string;
  dealstage?: string;
  pipeline?: string;
  closedate?: string;
  [key: string]: string | undefined;
}
