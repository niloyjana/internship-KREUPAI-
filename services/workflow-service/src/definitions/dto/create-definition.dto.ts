import { IsString, IsNotEmpty, IsOptional, IsObject } from 'class-validator';

export class CreateDefinitionDto {
  @IsString()
  @IsNotEmpty()
  agentId!: string;

  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsString()
  @IsNotEmpty()
  triggerType!: string;

  @IsObject()
  triggerConfig!: Record<string, unknown>;

  @IsObject()
  stepsJson!: Record<string, unknown>;

  @IsString()
  @IsOptional()
  description?: string;
}
