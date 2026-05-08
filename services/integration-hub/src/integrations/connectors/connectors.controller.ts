import {
  Body,
  Controller,
  Get,
  Param,
  Post,
  Query,
} from '@nestjs/common';
import { CurrentUser } from '../../common/decorators/current-user.decorator';
import { Roles } from '../../common/decorators/roles.decorator';
import { ConnectorsService } from './connectors.service';
import { SendEmailDto } from '../dto/send-email.dto';
import { ListEmailsQueryDto } from '../dto/list-emails-query.dto';
import { ListContactsQueryDto } from '../dto/list-contacts-query.dto';
import { CreateContactDto } from '../dto/create-contact.dto';

/**
 * Exposes connector actions on existing integration connections.
 *
 * All routes live under:
 *   /v1/integrations/connections/:connectionId/actions/*
 *
 * Every endpoint requires an authenticated user with PLATFORM_ADMIN
 * or TENANT_ADMIN role and a CONNECTED integration.
 */
@Controller({ path: 'integrations/connections/:connectionId/actions', version: '1' })
@Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
export class ConnectorsController {
  constructor(private readonly connectorsService: ConnectorsService) {}

  // ── Gmail actions ─────────────────────────────────────────

  /**
   * POST /v1/integrations/connections/:connectionId/actions/send-email
   * Send an email through a Gmail connection.
   */
  @Post('send-email')
  async sendEmail(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Body() dto: SendEmailDto,
  ) {
    const data = await this.connectorsService.sendEmail(
      tenantId,
      connectionId,
      {
        to: dto.to,
        subject: dto.subject,
        body: dto.body,
        cc: dto.cc,
        bcc: dto.bcc,
        contentType: dto.contentType as 'text/plain' | 'text/html' | undefined,
      },
    );
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/connections/:connectionId/actions/list-emails
   * List emails from a Gmail connection.
   */
  @Get('list-emails')
  async listEmails(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Query() query: ListEmailsQueryDto,
  ) {
    const data = await this.connectorsService.listEmails(
      tenantId,
      connectionId,
      {
        query: query.query,
        maxResults: query.maxResults,
        pageToken: query.pageToken,
      },
    );
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/connections/:connectionId/actions/get-email/:messageId
   * Get a single email's full details from a Gmail connection.
   */
  @Get('get-email/:messageId')
  async getEmail(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Param('messageId') messageId: string,
  ) {
    const data = await this.connectorsService.getEmail(
      tenantId,
      connectionId,
      messageId,
    );
    return { success: true, data };
  }

  // ── HubSpot actions ───────────────────────────────────────

  /**
   * GET /v1/integrations/connections/:connectionId/actions/list-contacts
   * List contacts from a HubSpot connection.
   */
  @Get('list-contacts')
  async listContacts(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Query() query: ListContactsQueryDto,
  ) {
    const data = await this.connectorsService.listContacts(
      tenantId,
      connectionId,
      {
        limit: query.limit,
        after: query.after,
        properties: query.properties,
      },
    );
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/connections/:connectionId/actions/get-contact/:contactId
   * Get a single contact from a HubSpot connection.
   */
  @Get('get-contact/:contactId')
  async getContact(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Param('contactId') contactId: string,
    @Query('properties') properties?: string,
  ) {
    const propertyList = properties
      ? properties.split(',').map((p) => p.trim())
      : undefined;

    const data = await this.connectorsService.getContact(
      tenantId,
      connectionId,
      contactId,
      propertyList,
    );
    return { success: true, data };
  }

  /**
   * POST /v1/integrations/connections/:connectionId/actions/create-contact
   * Create a contact in a HubSpot connection.
   */
  @Post('create-contact')
  async createContact(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Body() dto: CreateContactDto,
  ) {
    const data = await this.connectorsService.createContact(
      tenantId,
      connectionId,
      {
        email: dto.email,
        firstname: dto.firstname,
        lastname: dto.lastname,
        phone: dto.phone,
        company: dto.company,
        jobtitle: dto.jobtitle,
      },
    );
    return { success: true, data };
  }

  /**
   * GET /v1/integrations/connections/:connectionId/actions/list-deals
   * List deals from a HubSpot connection.
   */
  @Get('list-deals')
  async listDeals(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Query() query: ListContactsQueryDto, // Same shape: limit, after, properties
  ) {
    const data = await this.connectorsService.listDeals(
      tenantId,
      connectionId,
      {
        limit: query.limit,
        after: query.after,
        properties: query.properties,
      },
    );
    return { success: true, data };
  }

  /**
   * POST /v1/integrations/connections/:connectionId/actions/create-deal
   * Create a deal in a HubSpot connection.
   */
  @Post('create-deal')
  async createDeal(
    @CurrentUser('tenantId') tenantId: string,
    @Param('connectionId') connectionId: string,
    @Body() body: { dealname: string; amount?: string; dealstage?: string; pipeline?: string; closedate?: string },
  ) {
    const data = await this.connectorsService.createDeal(
      tenantId,
      connectionId,
      body,
    );
    return { success: true, data };
  }
}
