import { IsOptional, IsString, IsIn } from 'class-validator';

export class AgentPerformanceQueryDto {
  @IsOptional()
  @IsString()
  from?: string;

  @IsOptional()
  @IsString()
  to?: string;

  @IsOptional()
  @IsIn(['daily', 'weekly', 'monthly'])
  granularity?: 'daily' | 'weekly' | 'monthly';
}
