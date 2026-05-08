/**
 * Deep-merge utility for AgentPolicyConfig objects.
 *
 * Recursively merges override values into a base config:
 *  - Dict values are merged recursively
 *  - Array values in override replace the base array entirely
 *  - Scalar values in override replace base values
 *  - Keys in override that don't exist in base are added
 *
 * @see P4_Tenant_Configuration_Model.md Section 1 & 3
 */
export function deepMergeConfigs(
  base: Record<string, unknown>,
  ...overrides: Record<string, unknown>[]
): Record<string, unknown> {
  const result: Record<string, unknown> = structuredClone(base);

  for (const override of overrides) {
    if (!override || typeof override !== 'object') continue;
    mergeInto(result, override);
  }

  return result;
}

function mergeInto(target: Record<string, unknown>, source: Record<string, unknown>): void {
  for (const key of Object.keys(source)) {
    const sourceVal = source[key];
    const targetVal = target[key];

    if (
      targetVal !== null &&
      targetVal !== undefined &&
      typeof targetVal === 'object' &&
      !Array.isArray(targetVal) &&
      sourceVal !== null &&
      sourceVal !== undefined &&
      typeof sourceVal === 'object' &&
      !Array.isArray(sourceVal)
    ) {
      mergeInto(targetVal as Record<string, unknown>, sourceVal as Record<string, unknown>);
    } else {
      target[key] = structuredClone(sourceVal);
    }
  }
}
