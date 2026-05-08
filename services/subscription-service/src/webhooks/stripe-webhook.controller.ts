import {
  Controller,
  Post,
  Req,
  Headers,
  HttpCode,
  HttpStatus,
  RawBodyRequest,
} from '@nestjs/common';
import { Request } from 'express';
import { Public } from '../common/decorators/public.decorator';
import { StripeWebhookService } from './stripe-webhook.service';

@Controller({ path: 'webhooks', version: '1' })
export class StripeWebhookController {
  constructor(private readonly stripeWebhookService: StripeWebhookService) {}

  /**
   * POST /v1/webhooks/stripe
   * Handle incoming Stripe webhook events.
   * This endpoint must be public (no JWT) and receives raw body for signature verification.
   */
  @Public()
  @Post('stripe')
  @HttpCode(HttpStatus.OK)
  async handleStripeWebhook(
    @Req() req: RawBodyRequest<Request>,
    @Headers('stripe-signature') signature: string,
  ) {
    const rawBody = req.rawBody;
    if (!rawBody) {
      return { success: false, error: 'RAW_BODY_REQUIRED' };
    }

    // Verify signature and construct event
    const event = this.stripeWebhookService.verifyAndConstructEvent(
      rawBody,
      signature,
    );

    // Route event to appropriate handler
    const result = await this.stripeWebhookService.handleWebhookEvent(event);

    return { success: true, data: result };
  }
}
