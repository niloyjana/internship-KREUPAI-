import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { randomUUID } from 'crypto';

export interface RuntimeExecuteRequest {
  executionId: string;
  tenantId: string;
  agentId: string;
  stepId: string;
  taskPayload: Record<string, unknown>;
  contextJson?: Record<string, unknown>;
  tenantConfig?: Record<string, unknown>;
  agentPolicy?: Record<string, unknown>;
}

export interface RuntimeExecuteResponse {
  executionId: string;
  stepId: string;
  status: 'completed' | 'failed' | 'escalated';
  output: Record<string, unknown>;
  durationMs: number;
  tokenUsed: number | null;
  costUsd: number | null;
  nextAction: string | null;
}

export interface RuntimeAgentStatus {
  agentId: string;
  registered: boolean;
  capabilities: string[];
  status: string;
}

@Injectable()
export class AiRuntimeService {
  private readonly logger = new Logger(AiRuntimeService.name);
  private readonly baseUrl: string;
  private readonly executeTimeoutMs: number;
  private readonly statusTimeoutMs: number;
  private readonly healthTimeoutMs: number;

  constructor(private readonly config: ConfigService) {
    this.baseUrl = this.config.get<string>('AI_RUNTIME_URL', 'http://localhost:8000');
    this.executeTimeoutMs = this.config.get<number>('AI_RUNTIME_EXECUTE_TIMEOUT_MS', 120_000);
    this.statusTimeoutMs = this.config.get<number>('AI_RUNTIME_STATUS_TIMEOUT_MS', 10_000);
    this.healthTimeoutMs = this.config.get<number>('AI_RUNTIME_HEALTH_TIMEOUT_MS', 5_000);
  }

  async executeAgent(request: RuntimeExecuteRequest): Promise<RuntimeExecuteResponse> {
    const url = `${this.baseUrl}/v1/agent/execute`;
    const requestId = randomUUID();

    this.logger.log(
      `Calling AI Runtime: agent=${request.agentId} execution=${request.executionId} requestId=${requestId}`,
    );

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': request.tenantId,
        'X-Request-ID': requestId,
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(this.executeTimeoutMs),
    });

    if (!response.ok) {
      const body = await response.text();
      this.logger.error(`AI Runtime error: ${response.status} ${body}`);
      throw new Error(`AI Runtime returned ${response.status}: ${body}`);
    }

    const result = (await response.json()) as RuntimeExecuteResponse;

    this.logger.log(
      `AI Runtime result: agent=${request.agentId} status=${result.status} duration=${result.durationMs}ms`,
    );

    return result;
  }

  async getAgentStatus(agentId: string): Promise<RuntimeAgentStatus> {
    const url = `${this.baseUrl}/v1/agent/${agentId}/status`;

    const response = await fetch(url, {
      headers: { 'X-Request-ID': randomUUID() },
      signal: AbortSignal.timeout(this.statusTimeoutMs),
    });

    if (!response.ok) {
      throw new Error(`AI Runtime returned ${response.status}`);
    }

    return (await response.json()) as RuntimeAgentStatus;
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/v1/health`, {
        signal: AbortSignal.timeout(this.healthTimeoutMs),
      });
      return response.ok;
    } catch (error) {
      this.logger.warn(
        `AI Runtime health check failed: ${error instanceof Error ? error.message : error}`,
      );
      return false;
    }
  }
}
