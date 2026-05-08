import { IsArray, IsBoolean, IsEnum, IsOptional, IsString, ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';
import { NotificationChannel } from '@prisma/client';

export class PreferenceItemDto {
  @IsString()
  eventType!: string;

  @IsArray()
  @IsEnum(NotificationChannel, { each: true })
  channels!: NotificationChannel[];

  @IsOptional()
  @IsBoolean()
  enabled?: boolean;
}

export class UpdatePreferencesDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => PreferenceItemDto)
  preferences!: PreferenceItemDto[];
}
