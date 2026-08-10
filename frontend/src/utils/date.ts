/**
 * Date helpers for NyaySetu Pro.
 *
 * Canonical internal/stored format: YYYY-MM-DD (predictable, sortable).
 * Display format (field + documents): DD-MM-YYYY — the app's existing legal style.
 *
 * We tolerate legacy values stored as DD-MM-YYYY / DD/MM/YYYY so saved cases
 * and drafts keep working.
 */

/** Date -> YYYY-MM-DD (local time, no TZ shifting). */
export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function twoDigits(s: string): string {
  return s.padStart(2, "0");
}

/**
 * Parse a stored date value into a Date.
 * Accepts YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY. Returns null when unparseable.
 */
export function parseDateValue(value: string | null | undefined): Date | null {
  if (!value) return null;
  const s = String(value).trim();
  if (!s) return null;
  let iso = s;
  // DD-MM-YYYY / DD/MM/YYYY -> YYYY-MM-DD
  const dmy = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
  if (dmy) iso = `${dmy[3]}-${twoDigits(dmy[2])}-${twoDigits(dmy[1])}`;
  const ymd = iso.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!ymd) return null;
  const y = Number(ymd[1]);
  const m = Number(ymd[2]);
  const d = Number(ymd[3]);
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  const dt = new Date(y, m - 1, d);
  // Reject invalid calendar dates (e.g. 2025-02-31)
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null;
  return dt;
}

/**
 * Format a stored value for display in the field, e.g. "20-01-2026".
 * Falls back to the raw string when unparseable so existing data is never hidden.
 */
export function formatDateDisplay(value: string | null | undefined): string {
  const d = parseDateValue(value);
  if (!d) return value ? String(value) : "";
  const dd = twoDigits(String(d.getDate()));
  const mm = twoDigits(String(d.getMonth() + 1));
  return `${dd}-${mm}-${d.getFullYear()}`;
}

/** True when the string is a canonical YYYY-MM-DD date. */
export function isISODate(value: string | null | undefined): boolean {
  if (!value) return false;
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value).trim()) && parseDateValue(value) !== null;
}
