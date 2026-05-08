import {
  IsArray,
  IsEmail,
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
} from 'class-validator';

export enum EmailContentType {
  PLAIN = 'text/plain',
  HTML = 'text/html',
}

export class SendEmailDto {
  @IsEmail()
  @IsNotEmpty()
  to!: string;

  @IsString()
  @IsNotEmpty()
  subject!: string;

  @IsString()
  @IsNotEmpty()
  body!: string;

  @IsArray()
  @IsEmail({}, { each: true })
  @IsOptional()
  cc?: string[];

  @IsArray()
  @IsEmail({}, { each: true })
  @IsOptional()
  bcc?: string[];

  @IsEnum(EmailContentType)
  @IsOptional()
  contentType?: EmailContentType;
}
