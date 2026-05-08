import { Logger } from '@nestjs/common';
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayInit,
  OnGatewayConnection,
  OnGatewayDisconnect,
  MessageBody,
  ConnectedSocket,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';

/**
 * WebSocket gateway for pushing real-time updates to the portal.
 *
 * Clients join tenant-scoped rooms:
 *   - `dashboard:<tenantId>`  -- dashboard KPI / live-feed updates
 *   - `tasks:<tenantId>`      -- task queue (executions + human tasks)
 *
 * P3 spec event types (server → client):
 *   - agent.status.changed
 *   - escalation.created
 *   - workflow.execution.completed
 *   - human.task.assigned
 *   - cost.alert
 */
@WebSocketGateway({
  cors: { origin: '*' },
  namespace: '/ws',
})
export class EventsGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
  private readonly logger = new Logger(EventsGateway.name);

  @WebSocketServer()
  server!: Server;

  /* ------------------------------------------------------------------ */
  /*  Lifecycle hooks                                                    */
  /* ------------------------------------------------------------------ */

  afterInit() {
    this.logger.log('WebSocket gateway initialised on namespace /ws');
  }

  handleConnection(client: Socket) {
    this.logger.debug(`Client connected: ${client.id}`);
  }

  handleDisconnect(client: Socket) {
    this.logger.debug(`Client disconnected: ${client.id}`);
  }

  /* ------------------------------------------------------------------ */
  /*  Subscription handlers (client -> server)                           */
  /* ------------------------------------------------------------------ */

  @SubscribeMessage('subscribe:dashboard')
  handleSubscribeDashboard(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { tenantId: string },
  ) {
    const room = `dashboard:${data.tenantId}`;
    client.join(room);
    this.logger.debug(`Client ${client.id} joined room ${room}`);
    return { event: 'subscribed', data: { room } };
  }

  @SubscribeMessage('subscribe:tasks')
  handleSubscribeTasks(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { tenantId: string },
  ) {
    const room = `tasks:${data.tenantId}`;
    client.join(room);
    this.logger.debug(`Client ${client.id} joined room ${room}`);
    return { event: 'subscribed', data: { room } };
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: agent.status.changed                                      */
  /* ------------------------------------------------------------------ */

  emitAgentStatusChanged(
    tenantId: string,
    payload: {
      tenantId: string;
      agentId: string;
      status: string;
      timestamp: string;
    },
  ) {
    this.server.to(`dashboard:${tenantId}`).emit('agent.status.changed', payload);
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: escalation.created                                        */
  /* ------------------------------------------------------------------ */

  emitEscalationCreated(
    tenantId: string,
    payload: {
      escalationId: string;
      agentId: string;
      severity: string;
      title: string;
      slaDeadlineAt: string;
    },
  ) {
    this.server
      .to(`dashboard:${tenantId}`)
      .to(`tasks:${tenantId}`)
      .emit('escalation.created', payload);
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: workflow.execution.completed                              */
  /* ------------------------------------------------------------------ */

  emitWorkflowExecutionCompleted(
    tenantId: string,
    payload: {
      executionId: string;
      agentId: string;
      status: string;
      summary: string;
    },
  ) {
    this.server
      .to(`dashboard:${tenantId}`)
      .to(`tasks:${tenantId}`)
      .emit('workflow.execution.completed', payload);
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: human.task.assigned                                       */
  /* ------------------------------------------------------------------ */

  emitHumanTaskAssigned(
    tenantId: string,
    payload: {
      taskId: string;
      title: string;
      priority: string;
      dueAt: string;
    },
  ) {
    this.server
      .to(`dashboard:${tenantId}`)
      .to(`tasks:${tenantId}`)
      .emit('human.task.assigned', payload);
  }

  /* ------------------------------------------------------------------ */
  /*  P3 Spec: cost.alert                                                */
  /* ------------------------------------------------------------------ */

  emitCostAlert(
    tenantId: string,
    payload: {
      agentId: string;
      dailySpendUsd: number;
      budgetLimitUsd: number;
      percentUsed: number;
    },
  ) {
    this.server.to(`dashboard:${tenantId}`).emit('cost.alert', payload);
  }

  /* ------------------------------------------------------------------ */
  /*  Internal helpers (used by Kafka consumers for dashboard refresh)   */
  /* ------------------------------------------------------------------ */

  emitDashboardMetrics(tenantId: string, payload: Record<string, any>) {
    this.server.to(`dashboard:${tenantId}`).emit('dashboard:metrics', payload);
  }
}
