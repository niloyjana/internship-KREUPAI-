import { Injectable, Logger } from '@nestjs/common';
import { CircuitBreakerRegistry } from '@adwp/utils';
import { StoredTokens } from '../../token-vault/token-vault.service';

// ── Interfaces ──────────────────────────────────────────────────

export interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: { dateTime: string; timeZone?: string };
  end: { dateTime: string; timeZone?: string };
  attendees?: Array<{ email: string; responseStatus?: string }>;
  location?: string;
  status: string;
  htmlLink?: string;
  organizer?: { email: string; displayName?: string };
}

export interface ListEventsParams {
  calendarId?: string;
  timeMin?: string;
  timeMax?: string;
  maxResults?: number;
  pageToken?: string;
  q?: string;
}

export interface ListEventsResult {
  items: CalendarEvent[];
  nextPageToken?: string;
  summary: string;
}

export interface CreateEventParams {
  calendarId?: string;
  summary: string;
  description?: string;
  start: { dateTime: string; timeZone?: string };
  end: { dateTime: string; timeZone?: string };
  attendees?: Array<{ email: string }>;
  location?: string;
}

export interface UpdateEventParams {
  calendarId?: string;
  eventId: string;
  summary?: string;
  description?: string;
  start?: { dateTime: string; timeZone?: string };
  end?: { dateTime: string; timeZone?: string };
  attendees?: Array<{ email: string }>;
  location?: string;
}

export interface FreeBusyParams {
  timeMin: string;
  timeMax: string;
  items: Array<{ id: string }>;
}

export interface FreeBusyResult {
  calendars: Record<string, { busy: Array<{ start: string; end: string }> }>;
}

const GCAL_API_BASE = 'https://www.googleapis.com/calendar/v3';

/**
 * Google Calendar integration connector.
 *
 * Uses plain fetch against the Google Calendar REST API v3.
 * Authentication is handled via the OAuth Bearer token
 * stored in the IntegrationConnection record.
 */
@Injectable()
export class GoogleCalendarConnector {
  private readonly logger = new Logger(GoogleCalendarConnector.name);
  private readonly circuitBreaker =
    CircuitBreakerRegistry.getInstance().getBreaker('GOOGLE_CALENDAR');

  // ── helpers ─────────────────────────────────────────────

  private buildHeaders(tokens: StoredTokens): Record<string, string> {
    return {
      Authorization: `Bearer ${tokens.accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  private async request<T>(
    method: string,
    path: string,
    tokens: StoredTokens,
    body?: unknown,
    queryParams?: Record<string, string>,
  ): Promise<T> {
    return this.circuitBreaker.execute(async () => {
      const url = new URL(`${GCAL_API_BASE}${path}`);
      if (queryParams) {
        for (const [key, value] of Object.entries(queryParams)) {
          url.searchParams.set(key, value);
        }
      }

      const headers = this.buildHeaders(tokens);

      const res = await fetch(url.toString(), {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(
          `Google Calendar API error — ${method} ${path} ${res.status}: ${errorBody}`,
        );
        throw new Error(`Google Calendar API returned ${res.status}: ${errorBody}`);
      }

      if (res.status === 204) {
        return {} as T;
      }

      return (await res.json()) as T;
    });
  }

  // ── public API ──────────────────────────────────────────

  /**
   * List events from a Google Calendar.
   */
  async listEvents(tokens: StoredTokens, params: ListEventsParams = {}): Promise<ListEventsResult> {
    const calendarId = params.calendarId ?? 'primary';
    const maxResults = Math.min(params.maxResults ?? 10, 250);

    const queryParams: Record<string, string> = {
      maxResults: String(maxResults),
      singleEvents: 'true',
      orderBy: 'startTime',
    };

    if (params.timeMin) queryParams.timeMin = params.timeMin;
    if (params.timeMax) queryParams.timeMax = params.timeMax;
    if (params.pageToken) queryParams.pageToken = params.pageToken;
    if (params.q) queryParams.q = params.q;

    try {
      const data = await this.request<{
        items: CalendarEvent[];
        nextPageToken?: string;
        summary: string;
      }>(
        'GET',
        `/calendars/${encodeURIComponent(calendarId)}/events`,
        tokens,
        undefined,
        queryParams,
      );

      this.logger.log(`Listed ${data.items.length} events from calendar ${calendarId}`);

      return {
        items: data.items,
        nextPageToken: data.nextPageToken,
        summary: data.summary,
      };
    } catch (error) {
      this.logger.error(
        'Failed to list events from Google Calendar',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Create a new calendar event.
   */
  async createEvent(tokens: StoredTokens, params: CreateEventParams): Promise<CalendarEvent> {
    const calendarId = params.calendarId ?? 'primary';

    try {
      const event = await this.request<CalendarEvent>(
        'POST',
        `/calendars/${encodeURIComponent(calendarId)}/events`,
        tokens,
        {
          summary: params.summary,
          description: params.description,
          start: params.start,
          end: params.end,
          attendees: params.attendees,
          location: params.location,
        },
      );

      this.logger.log(`Event created — id=${event.id}`);
      return event;
    } catch (error) {
      this.logger.error(
        'Failed to create event in Google Calendar',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Update an existing calendar event.
   */
  async updateEvent(tokens: StoredTokens, params: UpdateEventParams): Promise<CalendarEvent> {
    const calendarId = params.calendarId ?? 'primary';

    const body: Record<string, unknown> = {};
    if (params.summary !== undefined) body.summary = params.summary;
    if (params.description !== undefined) body.description = params.description;
    if (params.start !== undefined) body.start = params.start;
    if (params.end !== undefined) body.end = params.end;
    if (params.attendees !== undefined) body.attendees = params.attendees;
    if (params.location !== undefined) body.location = params.location;

    try {
      const event = await this.request<CalendarEvent>(
        'PATCH',
        `/calendars/${encodeURIComponent(calendarId)}/events/${params.eventId}`,
        tokens,
        body,
      );

      this.logger.log(`Event updated — id=${event.id}`);
      return event;
    } catch (error) {
      this.logger.error(
        `Failed to update event ${params.eventId} in Google Calendar`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Delete a calendar event.
   */
  async deleteEvent(tokens: StoredTokens, eventId: string, calendarId = 'primary'): Promise<void> {
    try {
      await this.request<void>(
        'DELETE',
        `/calendars/${encodeURIComponent(calendarId)}/events/${eventId}`,
        tokens,
      );

      this.logger.log(`Event deleted — id=${eventId}`);
    } catch (error) {
      this.logger.error(
        `Failed to delete event ${eventId} from Google Calendar`,
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }

  /**
   * Query free/busy information for given calendars.
   */
  async getFreeBusy(tokens: StoredTokens, params: FreeBusyParams): Promise<FreeBusyResult> {
    try {
      const result = await this.request<FreeBusyResult>('POST', '/freeBusy', tokens, {
        timeMin: params.timeMin,
        timeMax: params.timeMax,
        items: params.items,
      });

      this.logger.log(`FreeBusy query completed for ${params.items.length} calendars`);
      return result;
    } catch (error) {
      this.logger.error(
        'Failed to query free/busy from Google Calendar',
        error instanceof Error ? error.stack : undefined,
      );
      throw error;
    }
  }
}
