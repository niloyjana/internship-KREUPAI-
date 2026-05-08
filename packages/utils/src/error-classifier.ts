// ─── Error Classifier ────────────────────────────────────────────────────────
//
// Classifies errors into 6 failure categories per P6 Error Handling spec
// (Section 1). Each category maps to retry eligibility, max retries,
// base delay, and escalation requirements.

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Failure categories A–F per P6 spec Section 1.
 */
export enum ErrorCategory {
  /** A — Network timeout, connection reset, DNS failure */
  TRANSIENT = 'TRANSIENT',
  /** B — API throttle, quota exceeded */
  RATE_LIMIT = 'RATE_LIMIT',
  /** C — Validation failure, policy violation, data conflict */
  BUSINESS_RULE = 'BUSINESS_RULE',
  /** D — Service unavailable, data format change, auth expired */
  EXTERNAL_SYSTEM = 'EXTERNAL_SYSTEM',
  /** E — Hallucination, token limit, model unavailable, safety filter */
  AI_FAILURE = 'AI_FAILURE',
  /** F — DB connection pool, Kafka broker, Redis connection, disk space */
  INFRASTRUCTURE = 'INFRASTRUCTURE',
}

/**
 * Result of classifying an error.
 */
export interface ErrorClassification {
  category: ErrorCategory;
  retryEligible: boolean;
  maxRetries: number;
  baseDelayMs: number;
  escalationRequired: boolean;
}

// ─── Classification Rules ────────────────────────────────────────────────────

interface ClassificationRule {
  category: ErrorCategory;
  /** Patterns matched against error name + message (case-insensitive). */
  patterns: string[];
  retryEligible: boolean;
  maxRetries: number;
  baseDelayMs: number;
  escalationRequired: boolean;
}

const CLASSIFICATION_RULES: ClassificationRule[] = [
  // Category A — Transient
  {
    category: ErrorCategory.TRANSIENT,
    patterns: [
      'ECONNRESET',
      'ETIMEDOUT',
      'ECONNREFUSED',
      'ENOTFOUND',
      'ENETUNREACH',
      'EAI_AGAIN',
      'socket hang up',
      'network timeout',
      'connection reset',
      'dns failure',
      'AbortError',
      'TimeoutError',
      'ECONNABORTED',
    ],
    retryEligible: true,
    maxRetries: 3,
    baseDelayMs: 2000,
    escalationRequired: false,
  },
  // Category B — Rate Limit
  {
    category: ErrorCategory.RATE_LIMIT,
    patterns: [
      'rate limit',
      'too many requests',
      'throttl',
      'quota exceeded',
      'RateLimitError',
      '429',
    ],
    retryEligible: true,
    maxRetries: 3,
    baseDelayMs: 5000,
    escalationRequired: false,
  },
  // Category C — Business Rule
  {
    category: ErrorCategory.BUSINESS_RULE,
    patterns: [
      'validation',
      'policy violation',
      'data conflict',
      'BadRequestException',
      'ConflictException',
      'UnprocessableEntityException',
      'business rule',
      'constraint violation',
      'duplicate entry',
      '400',
      '409',
      '422',
    ],
    retryEligible: false,
    maxRetries: 0,
    baseDelayMs: 0,
    escalationRequired: false,
  },
  // Category D — External System
  {
    category: ErrorCategory.EXTERNAL_SYSTEM,
    patterns: [
      'service unavailable',
      'ServiceUnavailableError',
      'bad gateway',
      'gateway timeout',
      'auth expired',
      'token expired',
      'unauthorized',
      'forbidden',
      'CircuitBreakerOpenError',
      '401',
      '403',
      '502',
      '503',
      '504',
    ],
    retryEligible: true,
    maxRetries: 3,
    baseDelayMs: 2000,
    escalationRequired: false,
  },
  // Category E — AI Failure
  {
    category: ErrorCategory.AI_FAILURE,
    patterns: [
      'hallucination',
      'token limit',
      'context length',
      'model unavailable',
      'safety filter',
      'content filter',
      'content_policy',
      'max_tokens',
      'context_length_exceeded',
      'model_not_found',
      'InternalServerError',
    ],
    retryEligible: true,
    maxRetries: 2,
    baseDelayMs: 5000,
    escalationRequired: false,
  },
  // Category F — Infrastructure
  {
    category: ErrorCategory.INFRASTRUCTURE,
    patterns: [
      'connection pool',
      'pool exhausted',
      'kafka broker',
      'redis connection',
      'disk space',
      'ENOMEM',
      'ENOSPC',
      'PrismaClientKnownRequestError',
      'PrismaClientInitializationError',
      'OperationalError',
      'BrokerNotAvailable',
    ],
    retryEligible: true,
    maxRetries: 3,
    baseDelayMs: 500,
    escalationRequired: true,
  },
];

// ─── Default fallback ────────────────────────────────────────────────────────

const DEFAULT_CLASSIFICATION: ErrorClassification = {
  category: ErrorCategory.TRANSIENT,
  retryEligible: false,
  maxRetries: 0,
  baseDelayMs: 0,
  escalationRequired: true,
};

// ─── HTTP Status Code mapping ────────────────────────────────────────────────

const STATUS_CODE_CATEGORIES: Record<number, ErrorCategory> = {
  400: ErrorCategory.BUSINESS_RULE,
  401: ErrorCategory.EXTERNAL_SYSTEM,
  403: ErrorCategory.EXTERNAL_SYSTEM,
  404: ErrorCategory.BUSINESS_RULE,
  409: ErrorCategory.BUSINESS_RULE,
  422: ErrorCategory.BUSINESS_RULE,
  429: ErrorCategory.RATE_LIMIT,
  500: ErrorCategory.TRANSIENT,
  502: ErrorCategory.EXTERNAL_SYSTEM,
  503: ErrorCategory.EXTERNAL_SYSTEM,
  504: ErrorCategory.EXTERNAL_SYSTEM,
};

// ─── ErrorClassifier ─────────────────────────────────────────────────────────

/**
 * Classifies errors into P6-spec failure categories (A–F).
 *
 * Classification priority:
 * 1. HTTP status code (if present on the error)
 * 2. Pattern matching against error name + message
 * 3. Default: unclassified → non-retryable, escalation required
 *
 * @example
 * ```ts
 * const classifier = new ErrorClassifier();
 * const result = classifier.classify(new Error('rate limit exceeded'));
 * // result.category === ErrorCategory.RATE_LIMIT
 * // result.retryEligible === true
 * ```
 */
export class ErrorClassifier {
  /**
   * Classify an error into one of the 6 failure categories.
   */
  classify(error: Error): ErrorClassification {
    // 1. Check HTTP status code if available
    const statusCode = (error as any).status ?? (error as any).statusCode ?? (error as any).code;
    if (typeof statusCode === 'number' && STATUS_CODE_CATEGORIES[statusCode]) {
      const category = STATUS_CODE_CATEGORIES[statusCode];
      const rule = CLASSIFICATION_RULES.find((r) => r.category === category);
      if (rule) {
        return {
          category: rule.category,
          retryEligible: rule.retryEligible,
          maxRetries: rule.maxRetries,
          baseDelayMs: rule.baseDelayMs,
          escalationRequired: rule.escalationRequired,
        };
      }
    }

    // 2. Pattern matching against error name + message
    const searchText = `${error.name} ${error.message}`.toLowerCase();

    for (const rule of CLASSIFICATION_RULES) {
      const matched = rule.patterns.some((pattern) => searchText.includes(pattern.toLowerCase()));

      if (matched) {
        return {
          category: rule.category,
          retryEligible: rule.retryEligible,
          maxRetries: rule.maxRetries,
          baseDelayMs: rule.baseDelayMs,
          escalationRequired: rule.escalationRequired,
        };
      }
    }

    // 3. Default — unclassified
    return { ...DEFAULT_CLASSIFICATION };
  }
}
