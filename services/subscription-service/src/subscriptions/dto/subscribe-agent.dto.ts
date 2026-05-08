import { IsNotEmpty, IsString } from 'class-validator';

export class SubscribeAgentDto {
  @IsString()
  @IsNotEmpty()
  agentId!: string;
}
