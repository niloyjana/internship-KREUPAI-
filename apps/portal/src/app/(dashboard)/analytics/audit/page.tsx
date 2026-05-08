import { redirect } from 'next/navigation';

/**
 * Redirect /analytics/audit to /analytics/compliance for backwards compatibility.
 */
export default function AuditRedirectPage() {
  redirect('/analytics/compliance');
}
