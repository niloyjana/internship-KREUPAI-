# ADWP Security & Secrets Management Specification
## Security Architecture — AI Digital Workforce Platform
**File:** `docs/architecture/security-secrets-spec.md`
**Version:** 1.0.0

---

> This document defines HOW security is implemented operationally.
> The architecture document states WHAT security layers exist.
> This document tells every developer exactly what to implement and how.

---

## 1. Secret Classification

All secrets are classified into 4 tiers before storage decisions are made:

```
TIER 1 — PLATFORM SECRETS (highest protection)
  Examples: JWT signing keys, DB master credentials, KMS key ARNs, Stripe secret key
  Storage: AWS Secrets Manager (never Vault, never env files in production)
  Access: Platform engineers only via IAM role
  Rotation: Automatic (30-day cycle)
  In-code: Never hardcoded. Always loaded via SDK at startup.

TIER 2 — TENANT INTEGRATION TOKENS (high protection)
  Examples: OAuth access/refresh tokens, API keys for Salesforce/HubSpot/SAP
  Storage: AWS Secrets Manager with tenant-scoped path
  Access: integration-hub service only (via IAM role, no human access)
  Rotation: Auto-refresh before expiry. On-demand revocation on tenant offboard.
  In-code: Reference key stored in DB. Secret value NEVER in DB.
  Path format: /adwp/{env}/tenant/{tenantId}/integration/{connectionId}

TIER 3 — SERVICE-TO-SERVICE CREDENTIALS (medium protection)
  Examples: Internal service API keys, Kafka SASL credentials, Redis AUTH
  Storage: HashiCorp Vault (dynamic secrets preferred)
  Access: Service identity (Kubernetes service account)
  Rotation: Vault leases (24h for dynamic secrets, 7-day for static)

TIER 4 — NON-SECRET CONFIGURATION (standard protection)
  Examples: Feature flags, base URLs, timeouts, non-sensitive config
  Storage: Kubernetes ConfigMaps, environment variables
  Access: Standard application access
  Rotation: On config change via GitOps
```

---

## 2. JWT Architecture

### 2.1 Token Design

```typescript
// Access Token — short-lived (15 minutes)
interface AccessTokenPayload {
  sub: string;          // userId
  tid: string;          // tenantId
  role: UserRole;       // TENANT_ADMIN | END_USER | etc.
  dept?: string;        // department (optional)
  iat: number;          // issued at (Unix timestamp)
  exp: number;          // expiry (iat + 900 seconds)
  jti: string;          // unique token ID (for revocation)
}

// Refresh Token — long-lived (7 days)
interface RefreshTokenPayload {
  sub: string;          // userId
  tid: string;          // tenantId
  sessionId: string;    // maps to UserSession table
  iat: number;
  exp: number;          // iat + 604800 seconds
  jti: string;
}
```

### 2.2 JWT Signing

```typescript
// Key management for JWT signing
// File: services/auth-service/src/jwt/jwt.config.ts

// Algorithm: RS256 (asymmetric — sign with private, verify with public)
// Private key: AWS Secrets Manager → /adwp/{env}/jwt/private-key
// Public key:  Available to all services (Kubernetes ConfigMap)

// Key rotation process:
// 1. New key pair generated and stored in Secrets Manager
// 2. Old public key kept for 2x token lifetime (30 min overlap)
// 3. Token validation tries new key first, falls back to old key
// 4. Old key removed after overlap period

// NestJS JWT Module configuration:
JwtModule.registerAsync({
  useFactory: async (secretsService: SecretsService) => ({
    privateKey: await secretsService.get('/adwp/prod/jwt/private-key'),
    publicKey: await secretsService.get('/adwp/prod/jwt/public-key'),
    signOptions: {
      algorithm: 'RS256',
      expiresIn: '15m',
      issuer: 'adwp-auth-service',
      audience: 'adwp-platform'
    }
  })
})
```

### 2.3 Token Revocation

```typescript
// Refresh token revocation via Redis blocklist
// File: services/auth-service/src/jwt/token-revocation.service.ts

class TokenRevocationService {
  // Add JTI to blocklist (on logout, password change, suspicious activity)
  async revokeToken(jti: string, expirySeconds: number): Promise<void> {
    await this.redis.setex(`revoked:${jti}`, expirySeconds, '1');
  }

  // Check on every request
  async isRevoked(jti: string): Promise<boolean> {
    return await this.redis.exists(`revoked:${jti}`) === 1;
  }

  // Revoke all sessions for a user (on account suspension/compromise)
  async revokeAllUserSessions(userId: string): Promise<void> {
    const sessions = await this.db.userSession.findMany({
      where: { userId, expiresAt: { gt: new Date() } }
    });
    for (const session of sessions) {
      await this.revokeToken(session.token, 604800);
    }
    await this.db.userSession.updateMany({
      where: { userId },
      data: { expiresAt: new Date() }
    });
  }
}
```

---

## 3. Service-to-Service Authentication (mTLS)

```yaml
# All internal service communication uses mutual TLS
# Implemented via Kubernetes Istio service mesh

# Certificate authority: cert-manager (Let's Encrypt for external, self-signed for internal)
# Certificate rotation: Automatic (cert-manager renews 30 days before expiry)

# Istio PeerAuthentication — require mTLS for all service-to-service
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: adwp-prod
spec:
  mtls:
    mode: STRICT         # No plaintext allowed between services

# Authorization policy — workflow-service can only call ai-runtime
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: ai-runtime-access
  namespace: adwp-prod
spec:
  selector:
    matchLabels:
      app: ai-runtime
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/adwp-prod/sa/workflow-service"]
  - to:
    - operation:
        paths: ["/v1/agent/*"]
        methods: ["POST", "GET"]
```

---

## 4. Integration Token Vault

```typescript
// OAuth token storage — integration-hub service
// File: services/integration-hub/src/oauth/token-vault.service.ts

class IntegrationTokenVaultService {

  private readonly secretsClient: AWS.SecretsManager;

  // Secret path format: /adwp/{env}/tenant/{tenantId}/integration/{connectionId}
  private getSecretPath(tenantId: string, connectionId: string): string {
    return `/adwp/${process.env.ENV}/tenant/${tenantId}/integration/${connectionId}`;
  }

  // Store OAuth tokens (called after OAuth callback)
  async storeTokens(
    tenantId: string,
    connectionId: string,
    tokens: OAuthTokens
  ): Promise<void> {
    const secretValue = JSON.stringify({
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresAt: tokens.expiresAt,
      scope: tokens.scope,
      tokenType: tokens.tokenType,
      storedAt: new Date().toISOString()
    });

    await this.secretsClient.createOrUpdateSecret({
      Name: this.getSecretPath(tenantId, connectionId),
      SecretString: secretValue,
      Tags: [
        { Key: 'tenantId', Value: tenantId },
        { Key: 'connectionId', Value: connectionId },
        { Key: 'managed-by', Value: 'adwp-integration-hub' }
      ]
    });

    // Store ONLY the path reference in DB — never the token value
    await this.db.integrationConnection.update({
      where: { id: connectionId },
      data: {
        authSecretRef: this.getSecretPath(tenantId, connectionId),
        status: 'CONNECTED'
      }
    });
  }

  // Retrieve tokens (called before every integration API call)
  async getTokens(tenantId: string, connectionId: string): Promise<OAuthTokens> {
    const connection = await this.db.integrationConnection.findUnique({
      where: { id: connectionId }
    });

    if (!connection?.authSecretRef) {
      throw new IntegrationNotConnectedException(connectionId);
    }

    // Validate the requesting tenant owns this secret
    if (!connection.authSecretRef.includes(`/tenant/${tenantId}/`)) {
      throw new ForbiddenException('Cross-tenant token access denied');
    }

    const secret = await this.secretsClient.getSecretValue({
      SecretId: connection.authSecretRef
    });

    return JSON.parse(secret.SecretString);
  }

  // Auto-refresh tokens before expiry (called by scheduled job every 5 minutes)
  async refreshExpiringTokens(): Promise<void> {
    const expiringConnections = await this.db.integrationConnection.findMany({
      where: {
        status: 'CONNECTED',
        // Tokens expiring in next 15 minutes
      }
    });

    for (const conn of expiringConnections) {
      try {
        const tokens = await this.getTokens(conn.tenantId, conn.id);
        const expiresAt = new Date(tokens.expiresAt);
        const minutesUntilExpiry = (expiresAt.getTime() - Date.now()) / 60000;

        if (minutesUntilExpiry < 15) {
          const refreshed = await this.providerRefresh(conn.provider, tokens.refreshToken);
          await this.storeTokens(conn.tenantId, conn.id, refreshed);
        }
      } catch (error) {
        await this.markConnectionFailed(conn.id, error.message);
        await this.notifyConnectionFailure(conn);
      }
    }
  }

  // Revoke all tokens for a tenant (on offboarding)
  async revokeAllTenantTokens(tenantId: string): Promise<void> {
    const connections = await this.db.integrationConnection.findMany({
      where: { tenantId }
    });

    for (const conn of connections) {
      try {
        await this.secretsClient.deleteSecret({
          SecretId: conn.authSecretRef,
          ForceDeleteWithoutRecovery: false  // 30-day recovery window
        });
      } catch (e) {
        // Log and continue — don't fail offboarding
        this.logger.error(`Failed to delete secret for ${conn.id}: ${e.message}`);
      }
    }
  }
}
```

---

## 5. PII Detection & Redaction

```python
# ai-runtime/orchestrator/pii_redactor.py
# Applied to ALL data before sending to LLM

import re
from typing import Any

class PIIRedactor:
    """
    Detects and redacts PII from any text or JSON payload
    before it enters the LLM context window.
    """

    PII_PATTERNS = {
        'email':          r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone_intl':     r'\+?[0-9]{10,15}',
        'credit_card':    r'\b(?:\d{4}[\s-]?){3}\d{4}\b',
        'passport':       r'\b[A-Z]{1,2}[0-9]{6,9}\b',
        'iban':           r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b',
        'ssn_us':         r'\b(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0{4})\d{4}\b',
        'national_id_gcc':r'\b\d{9,12}\b',  # GCC national ID patterns
        'ip_address':     r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    }

    PII_REPLACEMENTS = {
        'email':           '[EMAIL_REDACTED]',
        'phone_intl':      '[PHONE_REDACTED]',
        'credit_card':     '[CARD_REDACTED]',
        'passport':        '[PASSPORT_REDACTED]',
        'iban':            '[IBAN_REDACTED]',
        'ssn_us':          '[SSN_REDACTED]',
        'national_id_gcc': '[ID_REDACTED]',
        'ip_address':      '[IP_REDACTED]',
    }

    def redact(self, text: str, agent_policy: dict) -> tuple[str, list[str]]:
        """
        Returns (redacted_text, list_of_detected_pii_types)
        Only redacts if piiRedactionEnabled = True in policy.
        """
        if not agent_policy.get('dataControls', {}).get('piiRedactionEnabled', True):
            return text, []

        detected = []
        redacted = text

        fields_to_redact = agent_policy.get('dataControls', {}).get(
            'piiFieldsToRedact',
            list(self.PII_PATTERNS.keys())
        )

        for pii_type in fields_to_redact:
            if pii_type in self.PII_PATTERNS:
                pattern = self.PII_PATTERNS[pii_type]
                if re.search(pattern, redacted, re.IGNORECASE):
                    detected.append(pii_type)
                    redacted = re.sub(
                        pattern,
                        self.PII_REPLACEMENTS[pii_type],
                        redacted,
                        flags=re.IGNORECASE
                    )

        return redacted, detected

    def redact_json(self, data: Any, agent_policy: dict) -> Any:
        """Recursively redact PII from nested JSON structures"""
        if isinstance(data, str):
            redacted, _ = self.redact(data, agent_policy)
            return redacted
        elif isinstance(data, dict):
            return {k: self.redact_json(v, agent_policy) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact_json(item, agent_policy) for item in data]
        return data
```

---

## 6. Encryption at Rest

```
DATABASE ENCRYPTION
═══════════════════
PostgreSQL (RDS):
  ├── Storage-level: AES-256 via AWS KMS (default KMS key per region)
  ├── Field-level encryption for ultra-sensitive columns:
  │     integration_connections.auth_json_encrypted  → encrypted in application layer
  │     users.mfa_secret                             → encrypted in application layer
  │     api_keys.key_hash                            → bcrypt (one-way)
  └── Encryption key: /adwp/{env}/db/field-encryption-key

FIELD-LEVEL ENCRYPTION IMPLEMENTATION
  // packages/utils/encryption.ts
  import { createCipheriv, createDecipheriv, randomBytes } from 'crypto';

  const ALGORITHM = 'aes-256-gcm';
  const KEY = Buffer.from(process.env.FIELD_ENCRYPTION_KEY, 'hex');

  export function encrypt(plaintext: string): string {
    const iv = randomBytes(16);
    const cipher = createCipheriv(ALGORITHM, KEY, iv);
    const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
    const authTag = cipher.getAuthTag();
    return [iv.toString('hex'), authTag.toString('hex'), encrypted.toString('hex')].join(':');
  }

  export function decrypt(ciphertext: string): string {
    const [ivHex, authTagHex, encryptedHex] = ciphertext.split(':');
    const decipher = createDecipheriv(ALGORITHM, KEY, Buffer.from(ivHex, 'hex'));
    decipher.setAuthTag(Buffer.from(authTagHex, 'hex'));
    return Buffer.concat([
      decipher.update(Buffer.from(encryptedHex, 'hex')),
      decipher.final()
    ]).toString('utf8');
  }

S3 / OBJECT STORAGE
  ├── Server-side encryption: SSE-S3 (AES-256)
  ├── Sensitive documents (contracts, payslips): SSE-KMS with tenant-specific CMK
  └── Bucket policy: Block all public access (no exceptions)

REDIS
  ├── Encryption in transit: TLS 1.3
  ├── Encryption at rest: ElastiCache encryption enabled
  └── No sensitive data stored in Redis (working memory only — non-PII context)
```

---

## 7. Network Security

```yaml
# Kubernetes Network Policy — deny all, allow explicit
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: adwp-prod
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]

# Allow specific service-to-service paths only
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: workflow-to-ai-runtime
spec:
  podSelector:
    matchLabels:
      app: ai-runtime
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: workflow-service
    ports:
    - port: 8000

# WAF Rules (AWS WAF / Cloudflare)
waf_rules:
  - name: "Block SQL Injection"
    rule: AWS-AWSManagedRulesSQLiRuleSet
  - name: "Block XSS"
    rule: AWS-AWSManagedRulesKnownBadInputsRuleSet
  - name: "Rate Limit Auth Endpoints"
    condition: "uri matches /v1/auth/login"
    limit: 20_per_minute_per_ip
    action: BLOCK
  - name: "Bot Protection"
    rule: AWS-AWSManagedRulesBotControlRuleSet
    mode: COUNT  # Monitor for 30 days before blocking
```

---

## 8. Security Incident Response Runbook

```
SEVERITY DEFINITIONS
═════════════════════
P1 CRITICAL:  Active breach, data exfiltration, ransomware, credential compromise
P2 HIGH:      Unauthorized access attempt (successful), vulnerability exploited
P3 MEDIUM:    Failed brute force (sustained), anomalous access patterns
P4 LOW:       Failed login spikes, outdated dependency with no exploit

P1 RESPONSE PROCEDURE
══════════════════════
T+0   Incident detected (AI Cybersecurity Analyst raises CRITICAL escalation)
T+5   Security lead paged via PagerDuty
T+10  Incident war room opened (Slack #incident-response channel)
T+15  Decision: contain (isolate affected tenant/service) vs monitor
T+30  Affected tenants notified if data at risk
T+60  Root cause investigation started
T+4h  Executive update
T+24h Post-incident report drafted
T+72h Full RCA delivered

CONTAINMENT ACTIONS (require security manager approval)
  ├── Revoke all sessions for affected user(s)
  ├── Disconnect affected integration connections
  ├── Isolate affected tenant (suspend API access temporarily)
  ├── Block suspicious IP ranges via WAF
  └── Rotate affected secrets immediately

NEVER DO DURING INCIDENT
  ✗ Delete logs or evidence (preserve forensic chain)
  ✗ Reboot affected systems without capturing state
  ✗ Communicate to press/external parties without comms team
  ✗ Guess — document assumptions separately from facts
```

---

## 9. Security Checklist for Developers

Before every PR that touches auth, data, or integrations:

```
CODE REVIEW SECURITY CHECKLIST
════════════════════════════════
Authentication & Authorization
  [ ] All endpoints have @Roles() decorator — no unprotected endpoints
  [ ] tenantId always extracted from JWT (never from request body)
  [ ] DB queries always include tenantId filter
  [ ] RLS SET app.tenant_id called in DB connection setup

Secrets
  [ ] No secrets in code, comments, or env files committed to Git
  [ ] No secrets logged (check all logger.log/debug calls)
  [ ] Secrets referenced via SecretsService, never process.env directly
  [ ] No secrets in error messages returned to client

Data
  [ ] PII fields identified and encrypted (field-level) where required
  [ ] LLM context goes through PIIRedactor before dispatch
  [ ] File uploads validated (type, size, virus scan)
  [ ] SQL: Prisma ORM used (no raw queries unless reviewed)

API
  [ ] Input validation via Zod/class-validator on all endpoints
  [ ] Rate limiting applied to new endpoints
  [ ] Error messages do not expose internal implementation details
  [ ] CORS configured restrictively (not *)

Audit
  [ ] All state-changing operations emit audit.event.recorded event
  [ ] Financial operations have before/after state captured
```

---

*AI Digital Workforce Platform | Security & Secrets Management Specification v1.0.0*
*Every developer must read this document before touching auth, payments, or integrations*
