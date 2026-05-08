// ─── Types ────────────────────────────────────────────────────────────────────

export interface RetryProfile {
  /** Maximum number of retry attempts (0 means no retries, execute once). */
  maxRetries: number;
  /** Base delay in milliseconds before the first retry. */
  baseDelayMs: number;
  /** Maximum delay cap in milliseconds. */
  maxDelayMs: number;
  /** Multiplier applied to the base delay on each successive retry. */
  backoffMultiplier: number;
}

// ─── Named Profiles ──────────────────────────────────────────────────────────

/**
 * Pre-defined retry profiles for common use cases.
 *
 * - `aggressive`: Fast retries with many attempts — use for idempotent internal calls.
 * - `standard`:   Balanced retry strategy — good default for most external APIs.
 * - `conservative`: Slow retries with few attempts — use for rate-limited or expensive calls.
 * - `none`: No retries — execute once and propagate any error immediately.
 */
export const RETRY_PROFILES: Record<string, RetryProfile> = {
  aggressive: {
    maxRetries: 5,
    baseDelayMs: 100,
    maxDelayMs: 5000,
    backoffMultiplier: 2,
  },
  standard: {
    maxRetries: 3,
    baseDelayMs: 500,
    maxDelayMs: 15000,
    backoffMultiplier: 2,
  },
  conservative: {
    maxRetries: 2,
    baseDelayMs: 2000,
    maxDelayMs: 30000,
    backoffMultiplier: 2,
  },
  none: {
    maxRetries: 0,
    baseDelayMs: 0,
    maxDelayMs: 0,
    backoffMultiplier: 1,
  },
};

// ─── Domain-Specific Retry Profiles (P6 Section 2) ──────────────────────────

/**
 * P6-spec domain-specific retry profiles.
 *
 * These are purpose-built for specific operation types and align exactly
 * with the values defined in P6 Error Handling spec Section 2.
 */
export const DOMAIN_RETRY_PROFILES: Record<string, RetryProfile> = {
  INTEGRATION_CALL: {
    maxRetries: 3,
    baseDelayMs: 2000,
    maxDelayMs: 30_000,
    backoffMultiplier: 2,
  },
  LLM_CALL: {
    maxRetries: 2,
    baseDelayMs: 5000,
    maxDelayMs: 60_000,
    backoffMultiplier: 2,
  },
  INTERNAL_SERVICE: {
    maxRetries: 3,
    baseDelayMs: 1000,
    maxDelayMs: 15_000,
    backoffMultiplier: 2,
  },
  KAFKA_PUBLISH: {
    maxRetries: 5,
    baseDelayMs: 1000,
    maxDelayMs: 30_000,
    backoffMultiplier: 2,
  },
  DATABASE: {
    maxRetries: 3,
    baseDelayMs: 500,
    maxDelayMs: 10_000,
    backoffMultiplier: 2,
  },
};

/**
 * Resolves a domain retry profile by name. Throws if unknown.
 */
export function getDomainRetryProfile(name: string): RetryProfile {
  const profile = DOMAIN_RETRY_PROFILES[name];
  if (!profile) {
    throw new Error(
      `Unknown domain retry profile "${name}". Available: ${Object.keys(DOMAIN_RETRY_PROFILES).join(', ')}`,
    );
  }
  return profile;
}

/**
 * Executes an async function with retry logic using a P6 domain-specific profile.
 *
 * Optionally accepts an `ErrorClassifier` to check retry eligibility per error
 * category before retrying. If no classifier is provided, all errors are retried
 * up to the profile's maxRetries limit.
 *
 * @param fn - The async function to execute (and potentially retry)
 * @param profileName - Domain retry profile name ('INTEGRATION_CALL' | 'LLM_CALL' | 'INTERNAL_SERVICE' | 'KAFKA_PUBLISH' | 'DATABASE')
 * @param classifier - Optional ErrorClassifier for category-aware retry decisions
 * @returns The resolved value of `fn`
 * @throws The last error encountered after all retries are exhausted
 *
 * @example
 * ```ts
 * const result = await withDomainRetry(() => callSalesforce(), 'INTEGRATION_CALL');
 * ```
 */
export async function withDomainRetry<T>(
  fn: () => Promise<T>,
  profileName: string,
  classifier?: { classify: (error: Error) => { retryEligible: boolean } },
): Promise<T> {
  const profile = getDomainRetryProfile(profileName);
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= profile.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt === profile.maxRetries) {
        break;
      }

      // If a classifier is provided, check retry eligibility
      if (classifier) {
        const classification = classifier.classify(lastError);
        if (!classification.retryEligible) {
          break;
        }
      }

      // Exponential backoff with jitter
      const exponentialDelay = profile.baseDelayMs * Math.pow(profile.backoffMultiplier, attempt);
      const jitter = Math.random() * profile.baseDelayMs;
      const delay = Math.min(exponentialDelay + jitter, profile.maxDelayMs);

      await sleep(delay);
    }
  }

  throw lastError;
}

// ─── Helper ──────────────────────────────────────────────────────────────────

/**
 * Resolves a retry profile by name. Throws if the profile name is unknown.
 */
export function getRetryProfile(name: string): RetryProfile {
  const profile = RETRY_PROFILES[name];
  if (!profile) {
    throw new Error(
      `Unknown retry profile "${name}". Available profiles: ${Object.keys(RETRY_PROFILES).join(', ')}`,
    );
  }
  return profile;
}

/**
 * Executes an async function with retry logic based on a named profile.
 *
 * Uses exponential backoff with jitter. The delay between retries is:
 *   min(baseDelayMs * backoffMultiplier^attempt + jitter, maxDelayMs)
 *
 * @param fn - The async function to execute (and potentially retry)
 * @param profileName - Name of the retry profile to use ('aggressive' | 'standard' | 'conservative' | 'none')
 * @returns The resolved value of `fn`
 * @throws The last error encountered after all retries are exhausted
 *
 * @example
 * ```ts
 * const result = await withRetry(() => fetchExternalApi(), 'standard');
 * ```
 */
export async function withRetry<T>(fn: () => Promise<T>, profileName: string): Promise<T> {
  const profile = getRetryProfile(profileName);
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= profile.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt === profile.maxRetries) {
        break;
      }

      // Exponential backoff with jitter
      const exponentialDelay = profile.baseDelayMs * Math.pow(profile.backoffMultiplier, attempt);
      const jitter = Math.random() * profile.baseDelayMs;
      const delay = Math.min(exponentialDelay + jitter, profile.maxDelayMs);

      await sleep(delay);
    }
  }

  throw lastError;
}

// ─── Internal ─────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
