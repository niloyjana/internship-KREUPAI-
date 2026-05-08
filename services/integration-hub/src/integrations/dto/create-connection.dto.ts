import {
  IsEnum,
  IsNotEmpty,
  IsObject,
  IsOptional,
  IsString,
} from 'class-validator';

export enum AuthTypeEnum {
  OAUTH2 = 'oauth2',
  API_KEY = 'api_key',
}

export class CreateConnectionDto {
  @IsString()
  @IsNotEmpty()
  provider!: string;

  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsEnum(AuthTypeEnum)
  @IsNotEmpty()
  authType!: AuthTypeEnum;

  @IsObject()
  @IsOptional()
  config?: Record<string, unknown>;
}
