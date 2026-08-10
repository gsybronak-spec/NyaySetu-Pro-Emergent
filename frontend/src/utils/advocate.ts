/** Display an advocate name as "Adv. <Name>" without double-prefixing. */
export function formatAdvocateName(name?: string | null, fallback = "Advocate"): string {
  const n = (name || "").trim();
  if (!n) return fallback;
  return /^adv\.?\s/i.test(n) ? n : `Adv. ${n}`;
}
