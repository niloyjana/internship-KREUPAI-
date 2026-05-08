import { IsOptional, IsString, IsEnum, IsBoolean, IsInt, Min, Max } from 'class-validator';
import { Transform, Type } from 'class-transformer';

export enum AgentDepartmentFilter {
  CUSTOMER_OPERATIONS = 'CUSTOMER_OPERATIONS',
  SALES_MARKETING = 'SALES_MARKETING',
  HR_PEOPLE_OPS = 'HR_PEOPLE_OPS',
  FINANCE_PROCUREMENT = 'FINANCE_PROCUREMENT',
  DELIVERY_OPS = 'DELIVERY_OPS',
  GOVERNANCE_RISK_CONTROL = 'GOVERNANCE_RISK_CONTROL',
}

export class CatalogQueryDto {
  @IsOptional()
  @IsEnum(AgentDepartmentFilter)
  department?: AgentDepartmentFilter;

  @IsOptional()
  @Transform(({ value }) => {
    if (value === 'true') return true;
    if (value === 'false') return false;
    return value;
  })
  @IsBoolean()
  isActive?: boolean;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number = 20;

  @IsOptional()
  @IsString()
  search?: string;
}
