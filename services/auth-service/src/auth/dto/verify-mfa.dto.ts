import { IsNotEmpty, IsString, Length, Matches } from 'class-validator';

export class VerifyMfaDto {
  @IsString()
  @IsNotEmpty()
  @Length(6, 6, { message: 'MFA code must be exactly 6 digits' })
  @Matches(/^\d{6}$/, { message: 'MFA code must contain only digits' })
  code!: string;
}
