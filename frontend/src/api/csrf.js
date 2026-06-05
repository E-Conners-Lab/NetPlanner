/**
 * CSRF token helpers (SEC-07 — double-submit cookie).
 *
 * The backend issues a readable `netplanner_csrf` cookie; the SPA echoes it in
 * the `X-CSRF-Token` header on every mutating request. These helpers are pure
 * (no imports) so both the Axios client and the raw `fetch` in `useStream` can
 * share them without a circular dependency.
 */

export const CSRF_COOKIE = 'netplanner_csrf';
export const CSRF_HEADER = 'X-CSRF-Token';

/** Read the current CSRF token from `document.cookie`, or null if unset. */
export function readCsrfToken() {
  if (typeof document === 'undefined' || !document.cookie) return null;
  const prefix = `${CSRF_COOKIE}=`;
  for (const part of document.cookie.split('; ')) {
    if (part.startsWith(prefix)) {
      return decodeURIComponent(part.slice(prefix.length));
    }
  }
  return null;
}
