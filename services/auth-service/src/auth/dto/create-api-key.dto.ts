import { IsNotEmpty, IsOptional, IsString, IsDateString } from 'class-validator';

export class CreateApiKeyDto {
  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsOptional()
  @IsDateString()
  expiresAt?: string;
}
