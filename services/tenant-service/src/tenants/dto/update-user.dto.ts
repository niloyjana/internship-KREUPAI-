import { IsEnum, IsOptional, IsString, MaxLength } from 'class-validator';

export enum UserRole {
  PLATFORM_ADMIN = 'PLATFORM_ADMIN',
  TENANT_ADMIN = 'TENANT_ADMIN',
  DEPARTMENT_MANAGER = 'DEPARTMENT_MANAGER',
  END_USER = 'END_USER',
  AUDITOR = 'AUDITOR',
}

export enum UserStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE',
  INVITED = 'INVITED',
  SUSPENDED = 'SUSPENDED',
}

export class UpdateUserDto {
  @IsEnum(UserRole)
  @IsOptional()
  role?: UserRole;

  @IsEnum(UserStatus)
  @IsOptional()
  status?: UserStatus;

  @IsString()
  @IsOptional()
  @MaxLength(100)
  department?: string;
}
