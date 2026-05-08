import {
  Injectable,
  Logger,
  NotFoundException,
  ConflictException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

export interface CreateTemplateData {
  name: string;
  subject: string;
  body: string;
  channel: string;
}

export interface UpdateTemplateData {
  name?: string;
  subject?: string;
  body?: string;
  channel?: string;
}

export interface RenderResult {
  subject: string;
  body: string;
}

@Injectable()
export class TemplatesService {
  private readonly logger = new Logger(TemplatesService.name);

  constructor(private readonly prisma: PrismaService) {}

  // ----------------------------------------------------------------
  // LIST TEMPLATES
  // ----------------------------------------------------------------

  async listTemplates(tenantId: string) {
    const templates = await this.prisma.notificationTemplate.findMany({
      where: { tenantId },
      orderBy: { createdAt: 'desc' },
    });

    return templates;
  }

  // ----------------------------------------------------------------
  // CREATE TEMPLATE
  // ----------------------------------------------------------------

  async createTemplate(tenantId: string, data: CreateTemplateData) {
    // Ensure unique name per tenant
    const existing = await this.prisma.notificationTemplate.findFirst({
      where: { tenantId, name: data.name },
    });

    if (existing) {
      throw new ConflictException(
        `Template with name "${data.name}" already exists`,
      );
    }

    const template = await this.prisma.notificationTemplate.create({
      data: {
        tenantId,
        name: data.name,
        subject: data.subject,
        body: data.body,
        channel: data.channel,
      },
    });

    this.logger.log(`Template created: ${template.id} (${template.name})`);
    return template;
  }

  // ----------------------------------------------------------------
  // UPDATE TEMPLATE
  // ----------------------------------------------------------------

  async updateTemplate(
    tenantId: string,
    templateId: string,
    data: UpdateTemplateData,
  ) {
    const template = await this.prisma.notificationTemplate.findFirst({
      where: { id: templateId, tenantId },
    });

    if (!template) {
      throw new NotFoundException('TEMPLATE_NOT_FOUND');
    }

    // If renaming, check for conflicts
    if (data.name && data.name !== template.name) {
      const conflict = await this.prisma.notificationTemplate.findFirst({
        where: { tenantId, name: data.name },
      });
      if (conflict) {
        throw new ConflictException(
          `Template with name "${data.name}" already exists`,
        );
      }
    }

    const updated = await this.prisma.notificationTemplate.update({
      where: { id: templateId },
      data: {
        ...(data.name !== undefined && { name: data.name }),
        ...(data.subject !== undefined && { subject: data.subject }),
        ...(data.body !== undefined && { body: data.body }),
        ...(data.channel !== undefined && { channel: data.channel }),
      },
    });

    this.logger.log(`Template updated: ${updated.id} (${updated.name})`);
    return updated;
  }

  // ----------------------------------------------------------------
  // RENDER TEMPLATE
  // ----------------------------------------------------------------

  async renderTemplate(
    tenantId: string,
    templateId: string,
    variables: Record<string, string>,
  ): Promise<RenderResult> {
    const template = await this.prisma.notificationTemplate.findFirst({
      where: { id: templateId, tenantId },
    });

    if (!template) {
      throw new NotFoundException('TEMPLATE_NOT_FOUND');
    }

    const renderedSubject = this.interpolate(template.subject, variables);
    const renderedBody = this.interpolate(template.body, variables);

    return {
      subject: renderedSubject,
      body: renderedBody,
    };
  }

  // ----------------------------------------------------------------
  // PRIVATE HELPERS
  // ----------------------------------------------------------------

  /**
   * Replace {{variable}} placeholders in a string with provided values.
   * Unmatched placeholders are left as-is.
   */
  private interpolate(
    template: string,
    variables: Record<string, string>,
  ): string {
    return template.replace(/\{\{(\w+)\}\}/g, (match, key: string) => {
      return variables[key] !== undefined ? variables[key] : match;
    });
  }
}
