import { Controller, Get, Query } from '@nestjs/common';
import { Public } from '../common/decorators/public.decorator';
import { IntegrationsService } from './integrations.service';
import { OAuthCallbackQueryDto } from './dto/oauth-callback-query.dto';

@Controller({ path: 'integrations/oauth', version: '1' })
export class OAuthController {
  constructor(private readonly integrationsService: IntegrationsService) {}

  /**
   * GET /v1/integrations/oauth/callback
   * OAuth callback handler. Receives ?code=XXX&state=YYY.
   * This endpoint is @Public() — no JWT required.
   */
  @Public()
  @Get('callback')
  async oauthCallback(@Query() query: OAuthCallbackQueryDto) {
    const data = await this.integrationsService.handleOAuthCallback(
      query.code,
      query.state,
    );
    return { success: true, data };
  }
}
