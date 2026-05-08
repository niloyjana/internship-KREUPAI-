export interface IntegrationConnectedPayload {
  connectionId: string;
  provider: string;
  name: string;
  status: 'CONNECTED';
  scopesGranted: string[];
}

export interface IntegrationConnectionFailedPayload {
  connectionId: string;
  provider: string;
  errorType:
    | 'auth_expired'
    | 'rate_limited'
    | 'endpoint_unreachable'
    | 'permission_denied'
    | string;
  errorMessage: string;
  retryAfterSeconds: number | null;
}

export interface IntegrationTokenRefreshedPayload {
  connectionId: string;
  provider: string;
  expiresAt: string;
}
