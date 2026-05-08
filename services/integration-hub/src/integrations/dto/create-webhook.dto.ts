import {
  ArrayMinSize,
  IsArray,
  IsNotEmpty,
  IsOptional,
  IsString,
  IsUrl,
} from 'class-validator';

export class CreateWebhookDto {
  /**
   * The URL that will receive webhook event notifications.
   * Must be a valid HTTPS URL in production; HTTP is allowed in development.
   */
  @IsUrl({ require_tld: false }, { message: 'url must be a valid URL' })
  @IsNotEmpty()
  url!: string;

  /**
   * List of event types this webhook should be notified about.
   * Example: ['integration.connected', 'integration.token.refreshed']
   */
  @IsArray()
  @ArrayMinSize(1, { message: 'events must contain at least one event type' })
  @IsString({ each: true })
  events!: string[];

  /**
   * Optional shared secret used to sign webhook payloads (HMAC-SHA256).
   * The consumer can verify the signature to ensure the payload was not tampered with.
   */
  @IsOptional()
  @IsString()
  secret?: string;
}
