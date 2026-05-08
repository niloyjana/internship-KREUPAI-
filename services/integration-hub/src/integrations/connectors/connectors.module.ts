import { Module } from '@nestjs/common';
import { TokenVaultModule } from '../../token-vault/token-vault.module';
import { GmailConnector } from './gmail.connector';
import { HubSpotConnector } from './hubspot.connector';
import { SalesforceConnector } from './salesforce.connector';
import { GoogleCalendarConnector } from './google-calendar.connector';
import { OutlookConnector } from './outlook.connector';
import { SlackConnector } from './slack.connector';
import { JiraConnector } from './jira.connector';
import { QuickBooksConnector } from './quickbooks.connector';
import { XeroConnector } from './xero.connector';
import { ServiceNowConnector } from './servicenow.connector';
import { ConnectorFactory } from './connector.factory';
import { ConnectorsService } from './connectors.service';
import { ConnectorsController } from './connectors.controller';

@Module({
  imports: [TokenVaultModule],
  controllers: [ConnectorsController],
  providers: [
    GmailConnector,
    HubSpotConnector,
    SalesforceConnector,
    GoogleCalendarConnector,
    OutlookConnector,
    SlackConnector,
    JiraConnector,
    QuickBooksConnector,
    XeroConnector,
    ServiceNowConnector,
    ConnectorFactory,
    ConnectorsService,
  ],
  exports: [ConnectorsService, ConnectorFactory],
})
export class ConnectorsModule {}
