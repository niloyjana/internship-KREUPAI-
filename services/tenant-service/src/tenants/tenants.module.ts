import { Module } from '@nestjs/common';
import { TenantsController } from './tenants.controller';
import { TenantsConsumer } from './tenants.consumer';
import { TenantsService } from './tenants.service';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [AuthModule],
  controllers: [TenantsController, TenantsConsumer],
  providers: [TenantsService],
  exports: [TenantsService],
})
export class TenantsModule {}
