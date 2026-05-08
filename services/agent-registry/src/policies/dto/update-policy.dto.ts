import {
  IsNotEmpty,
  IsObject,
  IsOptional,
  IsString,
  MaxLength,
} from 'class-validator';

export class UpdatePolicyDto {
  @IsNotEmpty()
  @IsObject()
  policyJson!: Record<string, unknown>;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  changeReason?: string;
}
