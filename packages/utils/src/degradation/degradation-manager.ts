// ─── Graceful Degradation Manager (P6 Section 8) ─────────────────────────────
//
// 5-level degradation system that tracks service health and automatically
// transitions between operational levels based on dependency status.

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Degradation levels per P6 spec Section 8.
 * Lower value = healthier.
 */
export enum DegradationLevel {
  /** Level 1: All systems operational. */
  FULL_SERVICE = 1,
  /** Level 2: Cache stale data, skip non-critical integrations. */
  REDUCED_INTEGRATION = 2,
  /** Level 3: Use template responses instead of LLM. */
  LLM_FALLBACK = 3,
  /** Level 4: Queue tasks, notify admin. */
  AGENT_SUSPENDED = 4,
  /** Level 5: Serve cached data only, no writes. */
  READ_ONLY = 5,
}

export type OperationType = 'read' | 'write' | 'integration' | 'llm' | 'agent';

export interface DependencyHealth {
  name: string;
  status: 'up' | 'down' | 'degraded';
  critical: boolean;
}

interface ServiceState {
  level: DegradationLevel;
  since: number;
  reason: string;
}

// ─── Allowed operations per level ────────────────────────────────────────────

const LEVEL_PERMISSIONS: Record<DegradationLevel, Set<OperationType>> = {
  [DegradationLevel.FULL_SERVICE]: new Set(['read', 'write', 'integration', 'llm', 'agent']),
  [DegradationLevel.REDUCED_INTEGRATION]: new Set(['read', 'write', 'llm', 'agent']),
  [DegradationLevel.LLM_FALLBACK]: new Set(['read', 'write', 'agent']),
  [DegradationLevel.AGENT_SUSPENDED]: new Set(['read', 'write']),
  [DegradationLevel.READ_ONLY]: new Set(['read']),
};

// ─── DegradationManager ──────────────────────────────────────────────────────

/**
 * Singleton manager that tracks degradation level per service key
 * and provides automatic level transitions based on dependency health.
 *
 * @example
 * ```ts
 * const manager = DegradationManager.getInstance();
 *
 * // Check and transition based on health
 * manager.checkAndTransition('workflow-service', [
 *   { name: 'database', status: 'up', critical: true },
 *   { name: 'redis', status: 'down', critical: false },
 * ]);
 *
 * // Check if an operation is allowed
 * if (manager.isOperationAllowed('workflow-service', 'llm')) {
 *   // proceed with LLM call
 * }
 * ```
 */
export class DegradationManager {
  private static instance: DegradationManager | null = null;
  private readonly states = new Map<string, ServiceState>();

  private constructor() {}

  static getInstance(): DegradationManager {
    if (!DegradationManager.instance) {
      DegradationManager.instance = new DegradationManager();
    }
    return DegradationManager.instance;
  }

  /**
   * Get the current degradation level for a service.
   * Defaults to FULL_SERVICE if not tracked.
   */
  getLevel(serviceKey: string): DegradationLevel {
    return this.states.get(serviceKey)?.level ?? DegradationLevel.FULL_SERVICE;
  }

  /**
   * Get full state info for a service.
   */
  getState(serviceKey: string): ServiceState {
    return (
      this.states.get(serviceKey) ?? {
        level: DegradationLevel.FULL_SERVICE,
        since: Date.now(),
        reason: 'All systems operational',
      }
    );
  }

  /**
   * Check if a specific operation type is allowed at the current degradation level.
   */
  isOperationAllowed(serviceKey: string, operationType: OperationType): boolean {
    const level = this.getLevel(serviceKey);
    return LEVEL_PERMISSIONS[level].has(operationType);
  }

  /**
   * Evaluate dependency health and automatically transition degradation level.
   *
   * Transition rules:
   * - All deps UP → Level 1 (FULL_SERVICE)
   * - Any non-critical dep DOWN → Level 2 (REDUCED_INTEGRATION)
   * - LLM providers unavailable → Level 3 (LLM_FALLBACK)
   * - Multiple critical deps DOWN → Level 4 (AGENT_SUSPENDED)
   * - Database DOWN → Level 5 (READ_ONLY)
   */
  checkAndTransition(serviceKey: string, dependencies: DependencyHealth[]): DegradationLevel {
    const criticalDown = dependencies.filter((d) => d.critical && d.status === 'down');
    const nonCriticalDown = dependencies.filter((d) => !d.critical && d.status === 'down');
    const dbDown = dependencies.some(
      (d) => d.name === 'database' && d.status === 'down' && d.critical,
    );
    const llmDown = dependencies.some(
      (d) =>
        (d.name === 'llm' || d.name === 'openai' || d.name === 'anthropic') && d.status === 'down',
    );

    let newLevel: DegradationLevel;
    let reason: string;

    if (dbDown) {
      newLevel = DegradationLevel.READ_ONLY;
      reason = 'Database is DOWN — read-only mode';
    } else if (criticalDown.length >= 2) {
      newLevel = DegradationLevel.AGENT_SUSPENDED;
      reason = `Multiple critical deps DOWN: ${criticalDown.map((d) => d.name).join(', ')}`;
    } else if (llmDown) {
      newLevel = DegradationLevel.LLM_FALLBACK;
      reason = 'LLM provider unavailable — using fallback templates';
    } else if (nonCriticalDown.length > 0 || criticalDown.length === 1) {
      newLevel = DegradationLevel.REDUCED_INTEGRATION;
      reason = `Deps degraded: ${[...criticalDown, ...nonCriticalDown].map((d) => d.name).join(', ')}`;
    } else {
      newLevel = DegradationLevel.FULL_SERVICE;
      reason = 'All systems operational';
    }

    const currentState = this.states.get(serviceKey);

    if (!currentState || currentState.level !== newLevel) {
      this.states.set(serviceKey, {
        level: newLevel,
        since: Date.now(),
        reason,
      });
    }

    return newLevel;
  }

  /**
   * Manually set a degradation level (for admin overrides).
   */
  setLevel(serviceKey: string, level: DegradationLevel, reason: string): void {
    this.states.set(serviceKey, {
      level,
      since: Date.now(),
      reason,
    });
  }

  /**
   * Get status of all tracked services.
   */
  getAllStates(): Record<string, ServiceState> {
    const result: Record<string, ServiceState> = {};
    for (const [key, state] of this.states) {
      result[key] = state;
    }
    return result;
  }
}
