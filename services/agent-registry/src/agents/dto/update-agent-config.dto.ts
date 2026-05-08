import {
  IsOptional,
  IsString,
  IsObject,
  IsArray,
  MaxLength,
  MinLength,
} from 'class-validator';

export class UpdateAgentConfigDto {
  @IsOptional()
  @IsString()
  @MinLength(1)
  @MaxLength(100)
  displayName?: string;

  @IsOptional()
  @IsObject()
  policyJson?: Record<string, unknown>;

  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  integrationIds?: string[];

  @IsOptional()
  @IsString()
  @MaxLength(500)
  changeReason?: string;
}
