export enum CircuitState {
  CLOSED = 'CLOSED',
  OPEN = 'OPEN',
  HALF_OPEN = 'HALF_OPEN',
}

export interface CircuitBreakerOptions {
  failureThreshold?: number;
  resetTimeoutMs?: number;
}

const DEFAULT_OPTIONS: Required<CircuitBreakerOptions> = {
  failureThreshold: 5,
  resetTimeoutMs: 30000,
};

/**
 * Circuit Breaker pattern implementation.
 *
 * - CLOSED: Normal operation. Failures are counted.
 * - OPEN: Requests are rejected immediately. After resetTimeoutMs, transitions to HALF_OPEN.
 * - HALF_OPEN: A single request is allowed through. If it succeeds, transitions to CLOSED.
 *   If it fails, transitions back to OPEN.
 */
export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private lastFailureTime: number | null = null;
  private readonly failureThreshold: number;
  private readonly resetTimeoutMs: number;

  constructor(options?: CircuitBreakerOptions) {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    this.failureThreshold = opts.failureThreshold;
    this.resetTimeoutMs = opts.resetTimeoutMs;
  }

  /**
   * Returns the current state of the circuit breaker.
   */
  getState(): CircuitState {
    return this.state;
  }

  /**
   * Returns the current failure count.
   */
  getFailureCount(): number {
    return this.failureCount;
  }

  /**
   * Executes the given function through the circuit breaker.
   *
   * @param fn - The async function to execute
   * @returns The result of the function
   * @throws CircuitBreakerOpenError if the circuit is open
   * @throws The original error if the function fails
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (this.shouldAttemptReset()) {
        this.state = CircuitState.HALF_OPEN;
      } else {
        throw new CircuitBreakerOpenError(
          `Circuit breaker is OPEN. Retry after ${this.resetTimeoutMs}ms.`,
        );
      }
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

  /**
   * Manually reset the circuit breaker to CLOSED state.
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.lastFailureTime = null;
  }

  private shouldAttemptReset(): boolean {
    if (this.lastFailureTime === null) return false;
    return Date.now() - this.lastFailureTime >= this.resetTimeoutMs;
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.state = CircuitState.CLOSED;
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (
      this.failureCount >= this.failureThreshold ||
      this.state === CircuitState.HALF_OPEN
    ) {
      this.state = CircuitState.OPEN;
    }
  }
}

export class CircuitBreakerOpenError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CircuitBreakerOpenError';
  }
}
