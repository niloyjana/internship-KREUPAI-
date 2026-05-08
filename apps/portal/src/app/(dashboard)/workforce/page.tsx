import { redirect } from 'next/navigation';

/**
 * Redirect /workforce to /workforce/catalog.
 */
export default function WorkforcePage() {
  redirect('/workforce/catalog');
}
