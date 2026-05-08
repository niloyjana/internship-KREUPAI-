import {
  IsObject,
  IsOptional,
  IsString,
  IsUrl,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';

export class UpdateTenantDto {
  @IsString()
  @IsOptional()
  @MinLength(2)
  @MaxLength(100)
  name?: string;

  @IsString()
  @IsOptional()
  @MaxLength(50)
  timezone?: string;

  @IsObject()
  @IsOptional()
  config?: Record<string, any>;

  @IsString()
  @IsOptional()
  @IsUrl({}, { message: 'logoUrl must be a valid URL' })
  logoUrl?: string;

  @IsString()
  @IsOptional()
  @Matches(/^#[0-9A-Fa-f]{6}$/, {
    message: 'primaryColor must be a valid hex color (e.g. #FF5500)',
  })
  primaryColor?: string;
}
