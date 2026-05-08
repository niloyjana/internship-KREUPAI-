import {
  IsNotEmpty,
  IsString,
  IsObject,
  IsOptional,
  MaxLength,
  MinLength,
} from 'class-validator';

export class CreateTemplateDto {
  @IsNotEmpty()
  @IsString()
  @MinLength(1)
  @MaxLength(100)
  name!: string;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  description?: string;

  @IsNotEmpty()
  @IsObject()
  configJson!: Record<string, unknown>;

  @IsOptional()
  @IsString()
  @MaxLength(50)
  category?: string;
}
