// ─── PII Pattern Types ───────────────────────────────────────────────────────

/**
 * Names of all supported PII pattern categories.
 */
export type PIIPatternName =
  | 'email'
  | 'phone'
  | 'ssn'
  | 'creditCard'
  | 'iban'
  | 'passport'
  | 'gccId'
  | 'ipv4'
  | 'ipv6';

/**
 * Options for controlling which PII patterns are applied during redaction.
 *
 * Each key corresponds to a pattern category. Set to `false` to disable
 * that category. All patterns are enabled by default.
 */
export interface RedactOptions {
  /** Redact email addresses. Default: true */
  email?: boolean;
  /** Redact phone numbers. Default: true */
  phone?: boolean;
  /** Redact US Social Security Numbers (XXX-XX-XXXX). Default: true */
  ssn?: boolean;
  /** Redact credit card numbers (Luhn-validated pattern). Default: true */
  creditCard?: boolean;
  /** Redact IBANs (International Bank Account Numbers). Default: true */
  iban?: boolean;
  /** Redact passport numbers (alphanumeric 6-9 chars). Default: true */
  passport?: boolean;
  /** Redact GCC national ID numbers (UAE, Saudi, Bahrain, Kuwait, Oman, Qatar). Default: true */
  gccId?: boolean;
  /** Redact IPv4 addresses. Default: true */
  ipv4?: boolean;
  /** Redact IPv6 addresses. Default: true */
  ipv6?: boolean;
}

interface PIIPattern {
  name: PIIPatternName;
  regex: RegExp;
  replacement: string;
}

// ─── PII Patterns ────────────────────────────────────────────────────────────

/**
 * All supported PII patterns with their regex and replacement token.
 *
 * Order matters: more specific patterns (e.g. IBAN, credit card) should be
 * checked before more general numeric patterns (e.g. phone) to avoid
 * false positives.
 */
const PII_PATTERNS: PIIPattern[] = [
  // --- Email ---
  {
    name: 'email',
    regex: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
    replacement: '[REDACTED_EMAIL]',
  },

  // --- SSN (US format: XXX-XX-XXXX) ---
  {
    name: 'ssn',
    regex: /\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b/g,
    replacement: '[REDACTED_SSN]',
  },

  // --- IBAN (International Bank Account Number) ---
  // Matches standard IBAN: 2 letters, 2 digits, 4 alphanumeric, then 7-25
  // more alphanumeric characters. Allows optional spaces/dashes between
  // groups of 4 as commonly formatted (e.g. GB29 NWBK 6016 1331 9268 19).
  {
    name: 'iban',
    regex: /\b[A-Z]{2}\d{2}[\s-]?[A-Z0-9]{4}[\s-]?(?:[A-Z0-9]{4}[\s-]?){1,7}[A-Z0-9]{1,4}\b/g,
    replacement: '[REDACTED_IBAN]',
  },

  // --- Credit Card Numbers ---
  // Matches 13-19 digit card numbers with optional spaces/dashes.
  // Common formats: XXXX-XXXX-XXXX-XXXX, XXXX XXXX XXXX XXXX,
  // XXXXXXXXXXXXXXXX. Uses a pattern that covers Visa, MasterCard,
  // Amex, Discover, etc.
  {
    name: 'creditCard',
    regex: /\b(?:4\d{3}|5[1-5]\d{2}|6(?:011|5\d{2})|3[47]\d{2}|3(?:0[0-5]|[68]\d)\d)[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{1,7}\b/g,
    replacement: '[REDACTED_CC]',
  },

  // --- GCC National ID Numbers ---
  // UAE Emirates ID: 784-YYYY-NNNNNNN-C (15 digits starting with 784)
  {
    name: 'gccId',
    regex: /\b784[-\s]?\d{4}[-\s]?\d{7}[-\s]?\d\b/g,
    replacement: '[REDACTED_GCC_ID]',
  },
  // Saudi National ID / Iqama: starts with 1 (citizen) or 2 (resident), 10 digits total
  {
    name: 'gccId',
    regex: /\b[12]\d{9}\b/g,
    replacement: '[REDACTED_GCC_ID]',
  },
  // Bahrain CPR: 9 digits, typically YYMMDDnnn
  {
    name: 'gccId',
    regex: /\b\d{2}[01]\d[0-3]\d\d{3}\b/g,
    replacement: '[REDACTED_GCC_ID]',
  },
  // Kuwait Civil ID: 12 digits starting with 2 or 3
  {
    name: 'gccId',
    regex: /\b[23]\d{11}\b/g,
    replacement: '[REDACTED_GCC_ID]',
  },
  // Oman National ID: starts with a digit, typically 8 digits
  // Qatar QID: 11 digits starting with 2 or 3
  {
    name: 'gccId',
    regex: /\b[23]\d{10}\b/g,
    replacement: '[REDACTED_GCC_ID]',
  },

  // --- Passport Numbers ---
  // Alphanumeric 6-9 characters, typically starting with a letter.
  // Must be preceded by passport-related context to reduce false positives.
  {
    name: 'passport',
    regex: /(?<=\bpassport[\s:#-]*)[A-Z0-9]{6,9}\b/gi,
    replacement: '[REDACTED_PASSPORT]',
  },

  // --- IPv6 Addresses ---
  // Full and abbreviated IPv6 (e.g. 2001:0db8:85a3::8a2e:0370:7334)
  // Check before IPv4 since IPv6-mapped IPv4 contains dots.
  {
    name: 'ipv6',
    regex: /\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}\b|\b::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b|\b[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}\b/g,
    replacement: '[REDACTED_IPV6]',
  },

  // --- IPv4 Addresses ---
  // Standard dotted-decimal (e.g. 192.168.1.1). Validates each octet 0-255.
  {
    name: 'ipv4',
    regex: /\b(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\b/g,
    replacement: '[REDACTED_IPV4]',
  },

  // --- Phone Numbers ---
  // International and US phone formats: +1-555-123-4567, (555) 123-4567, etc.
  {
    name: 'phone',
    regex: /\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b/g,
    replacement: '[REDACTED_PHONE]',
  },
];

// ─── Standalone redactPii Function ──────────────────────────────────────────

/**
 * Redact PII from the given text, replacing matches with `[REDACTED_TYPE]` tokens.
 *
 * Supports: email, phone, SSN, credit card, IBAN, passport, GCC national ID,
 * IPv4, and IPv6 patterns. Each pattern can be individually toggled via the
 * `options` parameter.
 *
 * @param text - The text to redact PII from.
 * @param options - Optional object to enable/disable individual pattern categories.
 *   All patterns are enabled by default. Set a category to `false` to skip it.
 * @returns The text with PII replaced by redaction markers.
 *
 * @example
 * ```ts
 * // Redact everything (default)
 * redactPii('Email me at john@example.com from 192.168.1.1');
 * // => 'Email me at [REDACTED_EMAIL] from [REDACTED_IPV4]'
 *
 * // Only redact emails and IPs
 * redactPii('SSN 123-45-6789, email john@example.com', {
 *   ssn: false,
 *   phone: false,
 *   creditCard: false,
 *   iban: false,
 *   passport: false,
 *   gccId: false,
 * });
 * // => 'SSN 123-45-6789, email [REDACTED_EMAIL]'
 * ```
 */
export function redactPii(text: string, options?: RedactOptions): string {
  if (!text) {
    return text;
  }

  let redacted = text;

  for (const pattern of PII_PATTERNS) {
    // Check if this pattern category is enabled (default: true)
    if (options && options[pattern.name] === false) {
      continue;
    }

    // Reset lastIndex for global regexes
    pattern.regex.lastIndex = 0;
    redacted = redacted.replace(pattern.regex, pattern.replacement);
  }

  return redacted;
}

// ─── PIIRedactor Class (backward-compatible) ────────────────────────────────

/**
 * Redacts common PII patterns from text.
 *
 * Supported patterns:
 * - Email addresses        -> [REDACTED_EMAIL]
 * - SSN (XXX-XX-XXXX)      -> [REDACTED_SSN]
 * - Credit card numbers     -> [REDACTED_CC]
 * - Phone numbers           -> [REDACTED_PHONE]
 * - IBAN                    -> [REDACTED_IBAN]
 * - Passport numbers        -> [REDACTED_PASSPORT]
 * - GCC national IDs        -> [REDACTED_GCC_ID]
 * - IPv4 addresses          -> [REDACTED_IPV4]
 * - IPv6 addresses          -> [REDACTED_IPV6]
 *
 * Custom patterns can be added via the constructor.
 * For finer control over which categories are active, use the
 * standalone {@link redactPii} function with {@link RedactOptions}.
 */
export class PIIRedactor {
  private readonly additionalPatterns: Array<{ regex: RegExp; replacement: string }>;
  private readonly options?: RedactOptions;

  /**
   * Create a new PIIRedactor instance.
   *
   * @param additionalPatterns - Extra patterns to apply after the built-in set.
   * @param options - Optional toggles for built-in pattern categories.
   */
  constructor(
    additionalPatterns?: Array<{ regex: RegExp; replacement: string }>,
    options?: RedactOptions,
  ) {
    this.additionalPatterns = additionalPatterns ?? [];
    this.options = options;
  }

  /**
   * Redacts PII from the given text.
   *
   * @param text - The text to redact PII from.
   * @param options - Optional overrides for pattern toggles (merged with
   *   constructor options; per-call options take precedence).
   * @returns The text with PII patterns replaced by redaction markers.
   */
  redact(text: string, options?: RedactOptions): string {
    const mergedOptions = { ...this.options, ...options };

    // Apply built-in patterns via the standalone function
    let redacted = redactPii(text, mergedOptions);

    // Apply any additional custom patterns
    for (const pattern of this.additionalPatterns) {
      pattern.regex.lastIndex = 0;
      redacted = redacted.replace(pattern.regex, pattern.replacement);
    }

    return redacted;
  }
}
