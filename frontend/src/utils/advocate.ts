/** Display an advocate name with language-appropriate prefix without double-prefixing. */
export function formatAdvocateName(name?: string | null, language: "en" | "gu" = "en", fallback?: string): string {
  const n = (name || "").trim();
  if (!n) return fallback || (language === "gu" ? "એડવોકેટ" : "Advocate");
  if (language === "gu") {
    if (/^(એડવોકેટ|વકીલ|adv\.?)\s*/i.test(n)) {
      return n.replace(/^adv\.?\s*/i, "એડવોકેટ ");
    }
    return `એડવોકેટ ${n}`;
  } else {
    if (/^adv\.?\s/i.test(n)) return n;
    if (/^(એડવોકેટ|વકીલ)\s*/.test(n)) {
      return n.replace(/^(એડવોકેટ|વકીલ)\s*/, "Adv. ");
    }
    return `Adv. ${n}`;
  }
}

/** Formats a user display name cleanly without blindly adding "Adv." unless present in profile */
export function formatDisplayName(
  user?: { name?: string | null; advocate_name_en?: string | null; first_name?: string | null; last_name?: string | null; mobile?: string | null } | null,
  fallback = "Advocate"
): string {
  if (!user) return fallback;
  if (user.advocate_name_en && user.advocate_name_en.trim()) {
    return user.advocate_name_en.trim();
  }
  if (user.name && user.name.trim()) {
    return user.name.trim();
  }
  const parts = [user.first_name, user.last_name].filter(Boolean).map((s) => s!.trim()).join(" ");
  if (parts) return parts;
  return fallback;
}

