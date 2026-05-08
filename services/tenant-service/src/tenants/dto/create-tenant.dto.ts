import {
  IsEmail,
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';

export enum TenantPlan {
  STARTER = 'STARTER',
  GROWTH = 'GROWTH',
  ENTERPRISE = 'ENTERPRISE',
  CUSTOM = 'CUSTOM',
}

export class CreateTenantDto {
  @IsString()
  @IsNotEmpty()
  @MinLength(2)
  @MaxLength(100)
  name!: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(3)
  @MaxLength(50)
  @Matches(/^[a-z0-9]+(-[a-z0-9]+)*$/, {
    message:
      'Slug must be lowercase alphanumeric with hyphens, 3-50 chars (e.g. "my-company")',
  })
  slug!: string;

  @IsEnum(TenantPlan)
  @IsOptional()
  plan?: TenantPlan = TenantPlan.STARTER;

  @IsEmail()
  @IsNotEmpty()
  adminEmail!: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(2)
  @MaxLength(100)
  adminName!: string;

  @IsString()
  @IsOptional()
  @MaxLength(5)
  countryCode?: string = 'BH';

  @IsString()
  @IsOptional()
  @MaxLength(50)
  timezone?: string = 'UTC';
}
