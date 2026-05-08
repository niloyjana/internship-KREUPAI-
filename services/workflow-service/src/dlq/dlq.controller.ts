import { Controller, Get, Post, Param, Query, NotFoundException } from '@nestjs/common';
import { DlqService } from './dlq.service';
import { ListDlqQueryDto } from './dto';

@Controller({ path: 'dlq', version: '1' })
export class DlqController {
  constructor(private readonly dlqService: DlqService) {}

  /**
   * List DLQ entries with optional filtering by status, topic, and date range.
   */
  @Get()
  async listEntries(@Query() query: ListDlqQueryDto) {
    return this.dlqService.listEntries(query);
  }

  /**
   * Get aggregate DLQ statistics by status and topic.
   */
  @Get('stats')
  async getStats() {
    return this.dlqService.getStats();
  }

  /**
   * Manually replay a single DLQ entry by re-publishing to the original topic.
   */
  @Post(':id/replay')
  async replayEntry(@Param('id') id: string) {
    const result = await this.dlqService.replayEntry(id);

    if (result === null) {
      throw new NotFoundException(`DLQ entry not found: ${id}`);
    }

    return result;
  }
}
