import { IsString, IsNotEmpty, IsOptional, IsIn, IsObject } from 'class-validator';

export class ResolveTaskDto {
  @IsString()
  @IsNotEmpty()
  @IsIn(['approve', 'reject', 'modify'])
  decision!: string;

  @IsString()
  @IsOptional()
  decisionNote?: string;

  @IsObject()
  @IsOptional()
  modifiedPayload?: Record<string, unknown>;
}
