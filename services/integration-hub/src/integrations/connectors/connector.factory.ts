import { Injectable, BadRequestException } from '@nestjs/common';
import { IntegrationProvider } from '@prisma/client';
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

/**
 * Supported connector types returned by the factory.
 */
export type ConnectorInstance =
  | GmailConnector
  | HubSpotConnector
  | SalesforceConnector
  | GoogleCalendarConnector
  | OutlookConnector
  | SlackConnector
  | JiraConnector
  | QuickBooksConnector
  | XeroConnector
  | ServiceNowConnector;

/**
 * Factory that resolves the correct connector implementation
 * based on the IntegrationProvider enum value stored on a connection.
 */
@Injectable()
export class ConnectorFactory {
  constructor(
    private readonly gmailConnector: GmailConnector,
    private readonly hubSpotConnector: HubSpotConnector,
    private readonly salesforceConnector: SalesforceConnector,
    private readonly googleCalendarConnector: GoogleCalendarConnector,
    private readonly outlookConnector: OutlookConnector,
    private readonly slackConnector: SlackConnector,
    private readonly jiraConnector: JiraConnector,
    private readonly quickBooksConnector: QuickBooksConnector,
    private readonly xeroConnector: XeroConnector,
    private readonly serviceNowConnector: ServiceNowConnector,
  ) {}

  /**
   * Return the connector that handles the given provider.
   *
   * @throws BadRequestException when the provider has no connector yet.
   */
  getConnector(provider: IntegrationProvider): ConnectorInstance {
    switch (provider) {
      case IntegrationProvider.GMAIL:
        return this.gmailConnector;
      case IntegrationProvider.HUBSPOT:
        return this.hubSpotConnector;
      case IntegrationProvider.SALESFORCE:
        return this.salesforceConnector;
      case IntegrationProvider.GOOGLE_CALENDAR:
        return this.googleCalendarConnector;
      case IntegrationProvider.OUTLOOK:
        return this.outlookConnector;
      case IntegrationProvider.SLACK:
        return this.slackConnector;
      case IntegrationProvider.JIRA:
        return this.jiraConnector;
      case IntegrationProvider.QUICKBOOKS:
        return this.quickBooksConnector;
      case IntegrationProvider.XERO:
        return this.xeroConnector;
      case IntegrationProvider.SERVICENOW:
        return this.serviceNowConnector;
      default:
        throw new BadRequestException(
          `No connector implementation for provider "${provider}"`,
        );
    }
  }

  /**
   * Type-safe accessor for the Gmail connector.
   */
  getGmailConnector(): GmailConnector {
    return this.gmailConnector;
  }

  /**
   * Type-safe accessor for the HubSpot connector.
   */
  getHubSpotConnector(): HubSpotConnector {
    return this.hubSpotConnector;
  }

  /**
   * Type-safe accessor for the Salesforce connector.
   */
  getSalesforceConnector(): SalesforceConnector {
    return this.salesforceConnector;
  }

  /**
   * Type-safe accessor for the Google Calendar connector.
   */
  getGoogleCalendarConnector(): GoogleCalendarConnector {
    return this.googleCalendarConnector;
  }

  /**
   * Type-safe accessor for the Outlook connector.
   */
  getOutlookConnector(): OutlookConnector {
    return this.outlookConnector;
  }

  /**
   * Type-safe accessor for the Slack connector.
   */
  getSlackConnector(): SlackConnector {
    return this.slackConnector;
  }

  /**
   * Type-safe accessor for the Jira connector.
   */
  getJiraConnector(): JiraConnector {
    return this.jiraConnector;
  }

  /**
   * Type-safe accessor for the QuickBooks connector.
   */
  getQuickBooksConnector(): QuickBooksConnector {
    return this.quickBooksConnector;
  }

  /**
   * Type-safe accessor for the Xero connector.
   */
  getXeroConnector(): XeroConnector {
    return this.xeroConnector;
  }

  /**
   * Type-safe accessor for the ServiceNow connector.
   */
  getServiceNowConnector(): ServiceNowConnector {
    return this.serviceNowConnector;
  }
}
