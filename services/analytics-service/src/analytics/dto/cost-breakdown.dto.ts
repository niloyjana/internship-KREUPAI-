import { IsOptional, IsString, IsIn } from 'class-validator';

export class CostBreakdownQueryDto {
  @IsOptional()
  @IsIn(['agent', 'model'])
  groupBy?: 'agent' | 'model';

  @IsOptional()
  @IsIn(['daily', 'weekly', 'monthly'])
  period?: 'daily' | 'weekly' | 'monthly';

  @IsOptional()
  @IsString()
  from?: string;

  @IsOptional()
  @IsString()
  to?: string;
}
