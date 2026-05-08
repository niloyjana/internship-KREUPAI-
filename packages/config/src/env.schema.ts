import { z } from 'zod';

// ─── Environment Variable Schema ─────────────────────────────────────────────

export const envSchema = z.object({
  // Database
  DATABASE_URL: z.string().url('DATABASE_URL must be a valid URL'),

  // Redis
  REDIS_URL: z.string().url('REDIS_URL must be a valid URL'),

  // Kafka
  KAFKA_BROKERS: z.string().min(1, 'KAFKA_BROKERS is required'),

  // JWT
  JWT_PRIVATE_KEY: z.string().min(1, 'JWT_PRIVATE_KEY is required'),
  JWT_PUBLIC_KEY: z.string().min(1, 'JWT_PUBLIC_KEY is required'),
  JWT_ACCESS_EXPIRY: z.string().default('15m'),
  JWT_REFRESH_EXPIRY: z.string().default('7d'),

  // Encryption
  FIELD_ENCRYPTION_KEY: z.string().min(1, 'FIELD_ENCRYPTION_KEY is required'),

  // AI Providers (optional)
  OPENAI_API_KEY: z.string().optional(),
  ANTHROPIC_API_KEY: z.string().optional(),

  // Stripe (optional)
  STRIPE_SECRET_KEY: z.string().optional(),
  STRIPE_WEBHOOK_SECRET: z.string().optional(),

  // SendGrid (optional)
  SENDGRID_API_KEY: z.string().optional(),

  // Platform
  PLATFORM_URL: z.string().url('PLATFORM_URL must be a valid URL'),

  // Environment
  ENV: z.enum(['local', 'development', 'staging', 'production']).default('local'),

  // Tenant isolation strategy
  TENANT_ISOLATION_MODE: z.enum(['rls', 'schema']).default('rls'),
});

// ─── Inferred Type ────────────────────────────────────────────────────────────

export type EnvConfig = z.infer<typeof envSchema>;

// ─── Validation Function ──────────────────────────────────────────────────────

/**
 * Validates environment variables against the schema.
 *
 * @param env - The environment variables to validate (defaults to process.env)
 * @returns The validated and typed environment configuration
 * @throws ZodError if validation fails
 */
export function validateEnv(env: Record<string, string | undefined> = process.env): EnvConfig {
  const result = envSchema.safeParse(env);

  if (!result.success) {
    const formatted = result.error.issues
      .map((issue) => `  - ${issue.path.join('.')}: ${issue.message}`)
      .join('\n');

    throw new Error(
      `Environment variable validation failed:\n${formatted}`,
    );
  }

  return result.data;
}
