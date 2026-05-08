import { IsOptional, IsString } from 'class-validator';

export class EscalationTrendsQueryDto {
  @IsOptional()
  @IsString()
  from?: string;

  @IsOptional()
  @IsString()
  to?: string;

  @IsOptional()
  @IsString()
  agentId?: string;
}
