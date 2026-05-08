import {
  IsEmail,
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
  MaxLength,
  MinLength,
} from 'class-validator';

export enum UserRole {
  PLATFORM_ADMIN = 'PLATFORM_ADMIN',
  TENANT_ADMIN = 'TENANT_ADMIN',
  DEPARTMENT_MANAGER = 'DEPARTMENT_MANAGER',
  END_USER = 'END_USER',
  AUDITOR = 'AUDITOR',
}

export class InviteUserDto {
  @IsEmail()
  @IsNotEmpty()
  email!: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(2)
  @MaxLength(100)
  name!: string;

  @IsEnum(UserRole)
  @IsNotEmpty()
  role!: UserRole;

  @IsString()
  @IsOptional()
  @MaxLength(100)
  department?: string;
}
