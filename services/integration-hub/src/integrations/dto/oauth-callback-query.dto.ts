import { IsNotEmpty, IsString } from 'class-validator';

export class OAuthCallbackQueryDto {
  @IsString()
  @IsNotEmpty()
  code!: string;

  @IsString()
  @IsNotEmpty()
  state!: string;
}
