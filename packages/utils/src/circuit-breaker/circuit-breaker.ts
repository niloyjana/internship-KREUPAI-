// ─── Types ────────────────────────────────────────────────────────────────────

export enum CircuitState {
  CLOSED = 'CLOSED',
  OPEN = 'OPEN',
  HALF_OPEN = 'HALF_OPEN',
}

export interface CircuitBreakerConfig {
  /** Number of consecutive failures before the circuit opens. */
  failureThreshold: number;
  /** Time in milliseconds to wait before transitioning from OPEN to HALF_OPEN. */
  resetTimeoutMs: number;
  /** Maximum number of trial requests allowed in HALF_OPEN state. */
  halfOpenMaxAttempts: number;
}

// ─── Per-Provider Default Configs ─────────────────────────────────────────────

/**
 * Default circuit breaker configurations per integration provider.
 * These can be overridden when creating a CircuitBreaker instance.
 */
export const PROVIDER_CIRCUIT_CONFIGS: Record<string, CircuitBreakerConfig> = {
  HUBSPOT: {
    failureThreshold: 5,
    resetTimeoutMs: 30_000,
    halfOpenMaxAttempts: 2,
  },
  SALESFORCE: {
    failureThreshold: 5,
    resetTimeoutMs: 60_000,
    halfOpenMaxAttempts: 2,
  },
  GMAIL: {
    failureThreshold: 5,
    resetTimeoutMs: 30_000,
    halfOpenMaxAttempts: 3,
  },
  GOOGLE_CALENDAR: {
    failureThreshold: 5,
    resetTimeoutMs: 30_000,
    halfOpenMaxAttempts: 3,
  },
  OUTLOOK: {
    failureThreshold: 5,
    resetTimeoutMs: 45_000,
    halfOpenMaxAttempts: 2,
  },
  SLACK: {
    failureThreshold: 3,
    resetTimeoutMs: 20_000,
    halfOpenMaxAttempts: 2,
  },
  ODOO: {
    failureThreshold: 3,
    resetTimeoutMs: 15_000,
    halfOpenMaxAttempts: 1,
  },
  QUICKBOOKS: {
    failureThreshold: 5,
    resetTimeoutMs: 60_000,
    halfOpenMaxAttempts: 2,
  },
  XERO: {
    failureThreshold: 5,
    resetTimeoutMs: 60_000,
    halfOpenMaxAttempts: 2,
  },
  JIRA: {
    failureThreshold: 5,
    resetTimeoutMs: 30_000,
    halfOpenMaxAttempts: 2,
  },
  SAP: {
    failureThreshold: 3,
    resetTimeoutMs: 60_000,
    halfOpenMaxAttempts: 2,
  },
  OPENAI: {
    failureThreshold: 5,
    resetTimeoutMs: 45_000,
    halfOpenMaxAttempts: 2,
  },
  ANTHROPIC: {
    failureThreshold: 5,
    resetTimeoutMs: 45_000,
    halfOpenMaxAttempts: 2,
  },
  SENDGRID: {
    failureThreshold: 5,
    resetTimeoutMs: 30_000,
    halfOpenMaxAttempts: 2,
  },
  STRIPE: {
    failureThreshold: 3,
    resetTimeoutMs: 60_000,
    halfOpenMaxAttempts: 2,
  },
  SERVICENOW: {
    failureThreshold: 5,
    resetTimeoutMs: 30_000,
    halfOpenMaxAttempts: 2,
  },
};

/**
 * Fallback config used when no provider-specific config is found.
 */
export const DEFAULT_CIRCUIT_CONFIG: CircuitBreakerConfig = {
  failureThreshold: 5,
  resetTimeoutMs: 30_000,
  halfOpenMaxAttempts: 2,
};

// ─── CircuitBreaker Class ────────────────────────────────────────────────────

/**
 * Circuit Breaker pattern implementation with per-provider configuration
 * and half-open max attempt tracking.
 *
 * State transitions:
 * ```
 *   CLOSED ──(N failures)──> OPEN ──(timeout)──> HALF_OPEN
 *                                                    │
 *                                    success ─> CLOSED
 *                                    failure  ─> OPEN
 *                     (halfOpenMaxAttempts exhausted) ─> OPEN
 * ```
 *
 * @example
 * ```ts
 * // Use provider-specific defaults
 * const cb = CircuitBreaker.forProvider('HUBSPOT');
 * const result = await cb.execute(() => callHubSpotApi());
 *
 * // Use custom config
 * const cb2 = new CircuitBreaker({ failureThreshold: 3, resetTimeoutMs: 10000, halfOpenMaxAttempts: 1 });
 * ```
 */
export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private halfOpenAttempts = 0;
  private lastFailureTime: number | null = null;

  private readonly config: CircuitBreakerConfig;

  constructor(config?: Partial<CircuitBreakerConfig>) {
    this.config = { ...DEFAULT_CIRCUIT_CONFIG, ...config };
  }

  /**
   * Factory: creates a CircuitBreaker using the per-provider default config.
   * Falls back to DEFAULT_CIRCUIT_CONFIG if the provider is not in the map.
   */
  static forProvider(provider: string): CircuitBreaker {
    const providerConfig = PROVIDER_CIRCUIT_CONFIGS[provider];
    return new CircuitBreaker(providerConfig ?? DEFAULT_CIRCUIT_CONFIG);
  }

  /** Returns the current circuit state. */
  getState(): CircuitState {
    return this.state;
  }

  /** Returns the current consecutive failure count. */
  getFailureCount(): number {
    return this.failureCount;
  }

  /** Returns the active configuration. */
  getConfig(): Readonly<CircuitBreakerConfig> {
    return this.config;
  }

  /**
   * Executes the given async function through the circuit breaker.
   *
   * - CLOSED: normal execution; failures are counted.
   * - OPEN: rejects immediately with CircuitBreakerOpenError, unless the
   *   reset timeout has elapsed (transitions to HALF_OPEN).
   * - HALF_OPEN: allows up to `halfOpenMaxAttempts` trial requests. A success
   *   resets to CLOSED; a failure or exceeding max attempts reopens the circuit.
   *
   * @param fn - The async function to execute
   * @returns The result of `fn`
   * @throws CircuitBreakerOpenError when the circuit is OPEN
   * @throws The original error from `fn` when it fails
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (this.shouldAttemptReset()) {
        this.state = CircuitState.HALF_OPEN;
        this.halfOpenAttempts = 0;
      } else {
        throw new CircuitBreakerOpenError(
          `Circuit breaker is OPEN. Retry after ${this.config.resetTimeoutMs}ms.`,
        );
      }
    }

    // In HALF_OPEN, enforce max attempts
    if (this.state === CircuitState.HALF_OPEN) {
      if (this.halfOpenAttempts >= this.config.halfOpenMaxAttempts) {
        this.state = CircuitState.OPEN;
        this.lastFailureTime = Date.now();
        throw new CircuitBreakerOpenError(
          `Circuit breaker moved to OPEN after exhausting ${this.config.halfOpenMaxAttempts} half-open attempt(s).`,
        );
      }
      this.halfOpenAttempts++;
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  /** Manually reset the circuit breaker to CLOSED state. */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.halfOpenAttempts = 0;
    this.lastFailureTime = null;
  }

  // ─── Private ──────────────────────────────────────────────────────────────

  private shouldAttemptReset(): boolean {
    if (this.lastFailureTime === null) return false;
    return Date.now() - this.lastFailureTime >= this.config.resetTimeoutMs;
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.halfOpenAttempts = 0;
    this.state = CircuitState.CLOSED;
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (
      this.failureCount >= this.config.failureThreshold ||
      this.state === CircuitState.HALF_OPEN
    ) {
      this.state = CircuitState.OPEN;
    }
  }
}

// ─── Error ──────────────────────────────────────────────────────────────────

export class CircuitBreakerOpenError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CircuitBreakerOpenError';
  }
}

// ─── Registry ────────────────────────────────────────────────────────────────

/**
 * Singleton registry that lazily creates and caches one CircuitBreaker
 * per provider key. Use this instead of manually creating breakers
 * to ensure a single shared instance per integration.
 *
 * @example
 * ```ts
 * const registry = CircuitBreakerRegistry.getInstance();
 * const result = await registry.getBreaker('HUBSPOT').execute(() => callApi());
 * ```
 */
export class CircuitBreakerRegistry {
  private static instance: CircuitBreakerRegistry | null = null;
  private readonly breakers = new Map<string, CircuitBreaker>();

  private constructor() {}

  static getInstance(): CircuitBreakerRegistry {
    if (!CircuitBreakerRegistry.instance) {
      CircuitBreakerRegistry.instance = new CircuitBreakerRegistry();
    }
    return CircuitBreakerRegistry.instance;
  }

  /**
   * Get or create a CircuitBreaker for the given provider.
   * Uses the provider-specific config from PROVIDER_CIRCUIT_CONFIGS.
   */
  getBreaker(provider: string): CircuitBreaker {
    const key = provider.toUpperCase();
    let breaker = this.breakers.get(key);
    if (!breaker) {
      breaker = CircuitBreaker.forProvider(key);
      this.breakers.set(key, breaker);
    }
    return breaker;
  }

  /**
   * Returns the state of all registered circuit breakers.
   * Useful for health check endpoints and monitoring.
   */
  getStatus(): Record<string, { state: CircuitState; failureCount: number }> {
    const status: Record<string, { state: CircuitState; failureCount: number }> = {};
    for (const [key, breaker] of this.breakers) {
      status[key] = {
        state: breaker.getState(),
        failureCount: breaker.getFailureCount(),
      };
    }
    return status;
  }

  /** Reset all circuit breakers to CLOSED state. */
  resetAll(): void {
    for (const breaker of this.breakers.values()) {
      breaker.reset();
    }
  }
}
