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

export class CreateUserDto {
  @IsEmail()
  @IsNotEmpty()
  email!: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(1)
  @MaxLength(100)
  firstName!: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(1)
  @MaxLength(100)
  lastName!: string;

  @IsEnum(UserRole)
  @IsOptional()
  role?: UserRole = UserRole.END_USER;

  @IsString()
  @IsOptional()
  @MaxLength(100)
  department?: string;
}
