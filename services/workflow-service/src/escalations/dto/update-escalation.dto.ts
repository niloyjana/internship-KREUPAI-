import { IsOptional, IsString } from 'class-validator';

export class UpdateEscalationDto {
  @IsOptional()
  @IsString()
  assignedToUserId?: string;

  @IsOptional()
  @IsString()
  status?: string;

  @IsOptional()
  @IsString()
  resolutionNote?: string;
}
