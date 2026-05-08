import { BadRequestException } from '@nestjs/common';

/**
 * Config Validator — validates AgentPolicyConfig on every config save.
 *
 * Enforces:
 *  1. Field-level validation rules (min/max, allowed values)
 *  2. Cross-field validations
 *  3. Immutable platform constraints (cannot be overridden by any tenant)
 *
 * @see P4_Tenant_Configuration_Model.md Sections 5 & 8
 */

// ─── Field-level validation rules ────────────────────────────────────

interface NumericRule {
  type: 'numeric';
  min?: number;
  max?: number;
  rule: string;
}

interface AllowedValuesRule {
  type: 'allowedValues';
  allowedValues: string[];
  rule: string;
}

type ValidationRule = NumericRule | AllowedValuesRule;

const VALIDATION_RULES: Record<string, ValidationRule> = {
  'financialControls.autoApproveMaxAmountUsd': {
    type: 'numeric',
    min: 0,
    max: 10000,
    rule: 'Cannot exceed $10,000 auto-approve limit (platform maximum)',
  },
  'escalation.confidenceThreshold': {
    type: 'numeric',
    min: 0.5,
    max: 0.95,
    rule: 'Confidence threshold must be between 50% and 95%',
  },
  'communication.tone': {
    type: 'allowedValues',
    allowedValues: ['formal', 'professional_friendly', 'casual'],
    rule: 'Tone must be one of the allowed values',
  },
  'dataControls.dataRetentionDays': {
    type: 'numeric',
    min: 30,
    max: 2555,
    rule: 'Retention must be between 30 days and 7 years',
  },
  'payrollPolicy.gosiEmployeeRate': {
    type: 'numeric',
    min: 0,
    max: 0.2,
    rule: 'GOSI rate cannot exceed 20%',
  },
  'payrollPolicy.gosiEmployerRate': {
    type: 'numeric',
    min: 0,
    max: 0.2,
    rule: 'GOSI employer rate cannot exceed 20%',
  },
  'escalation.maxTaskDurationMinutes': {
    type: 'numeric',
    min: 1,
    max: 1440,
    rule: 'Max task duration must be between 1 and 1440 minutes',
  },
  'sla.firstResponseMinutes': {
    type: 'numeric',
    min: 1,
    max: 1440,
    rule: 'First response SLA must be between 1 and 1440 minutes',
  },
  'sla.resolutionHours': {
    type: 'numeric',
    min: 1,
    max: 720,
    rule: 'Resolution SLA must be between 1 and 720 hours',
  },
  'supportPolicy.autoApproveRefundMaxUsd': {
    type: 'numeric',
    min: 0,
    max: 10000,
    rule: 'Auto-approve refund cannot exceed $10,000',
  },
  'inventoryPolicy.targetServiceLevel': {
    type: 'numeric',
    min: 0.5,
    max: 1.0,
    rule: 'Target service level must be between 50% and 100%',
  },
};

// ─── Platform-level immutable constraints ────────────────────────────

interface PlatformConstraint {
  path: string;
  check: (value: unknown, fullConfig: Record<string, unknown>) => boolean;
  message: string;
}

const PLATFORM_CONSTRAINTS: PlatformConstraint[] = [
  {
    path: 'financialControls.autoApproveMaxAmountUsd',
    check: (v) => typeof v !== 'number' || v <= 10000,
    message: 'autoApproveMaxAmountUsd cannot exceed $10,000 (hard ceiling)',
  },
  {
    path: 'dataControls.dataRetentionDays',
    check: (v) => typeof v !== 'number' || v >= 30,
    message: 'dataRetentionDays cannot be less than 30 (minimum retention)',
  },
  {
    path: 'dataControls.crossTenantIsolationMode',
    check: (v) => v === undefined || v === null || v === 'strict' || v === 'standard',
    message: 'crossTenantIsolationMode cannot be weakened below "standard"',
  },
  {
    path: 'payrollPolicy.gosiEmployeeRate',
    check: (v) => typeof v !== 'number' || v >= 0,
    message: 'Statutory rates cannot be set below legal minimums',
  },
  {
    path: 'payrollPolicy.gosiEmployerRate',
    check: (v) => typeof v !== 'number' || v >= 0,
    message: 'Statutory rates cannot be set below legal minimums',
  },
];

// ─── Helpers ─────────────────────────────────────────────────────────

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    if (typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

// ─── Public API ──────────────────────────────────────────────────────

export interface ConfigValidationError {
  field: string;
  rule: string;
  value?: unknown;
}

export interface ConfigValidationResult {
  valid: boolean;
  errors: ConfigValidationError[];
}

/**
 * Validates an AgentPolicyConfig object against all rules and platform constraints.
 * Throws BadRequestException if validation fails (for use in NestJS controllers/services).
 */
export function validateAgentPolicyConfig(config: Record<string, unknown>): ConfigValidationResult {
  const errors: ConfigValidationError[] = [];

  // 1. Field-level validation
  for (const [path, rule] of Object.entries(VALIDATION_RULES)) {
    const value = getNestedValue(config, path);
    if (value === undefined || value === null) continue;

    if (rule.type === 'numeric') {
      if (typeof value !== 'number') {
        errors.push({ field: path, rule: `${path} must be a number`, value });
        continue;
      }
      if (rule.min !== undefined && value < rule.min) {
        errors.push({ field: path, rule: rule.rule, value });
      }
      if (rule.max !== undefined && value > rule.max) {
        errors.push({ field: path, rule: rule.rule, value });
      }
    }

    if (rule.type === 'allowedValues') {
      if (!rule.allowedValues.includes(value as string)) {
        errors.push({ field: path, rule: rule.rule, value });
      }
    }
  }

  // 2. Cross-field validations
  const confidenceThreshold = getNestedValue(config, 'escalation.confidenceThreshold') as
    | number
    | undefined;
  const maxTurns = getNestedValue(config, 'supportPolicy.maxTurnsBeforeEscalate') as
    | number
    | undefined;

  if (
    confidenceThreshold !== undefined &&
    confidenceThreshold > 0.9 &&
    maxTurns !== undefined &&
    maxTurns > 3
  ) {
    errors.push({
      field: 'escalation.confidenceThreshold + supportPolicy.maxTurnsBeforeEscalate',
      rule: 'If confidenceThreshold > 0.90, maxTurnsBeforeEscalate must be <= 3',
      value: { confidenceThreshold, maxTurns },
    });
  }

  // 3. Platform-level immutable constraints
  for (const constraint of PLATFORM_CONSTRAINTS) {
    const value = getNestedValue(config, constraint.path);
    if (value === undefined || value === null) continue;
    if (!constraint.check(value, config)) {
      errors.push({
        field: constraint.path,
        rule: constraint.message,
        value,
      });
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validates and throws BadRequestException if invalid.
 * Intended for use in NestJS service methods.
 */
export function assertValidPolicyConfig(config: Record<string, unknown>): void {
  const result = validateAgentPolicyConfig(config);
  if (!result.valid) {
    throw new BadRequestException({
      message: 'Policy config validation failed',
      errors: result.errors,
    });
  }
}

/**
 * Validates that platform constraints on an ENTERPRISE plan are enforced.
 * Enterprise plans have additional immutable constraints.
 */
export function assertEnterprisePlanConstraints(
  config: Record<string, unknown>,
  planTier: string,
): void {
  if (planTier !== 'ENTERPRISE') return;

  const auditEveryAction = getNestedValue(config, 'dataControls.auditEveryAction');
  if (auditEveryAction === false) {
    throw new BadRequestException('auditEveryAction cannot be set to false for ENTERPRISE plan');
  }
}
