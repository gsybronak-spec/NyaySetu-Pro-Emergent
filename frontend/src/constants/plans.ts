export interface CatalogPlan {
  id: string;
  name: string;
  price: number;
  credits: number;
  popular: boolean;
  per_template: number;
  description?: string;
  active?: boolean;
}

/**
 * Standard NyaySetu Pro Catalog Plans (matches backend seed data).
 * Used for instantaneous rendering so users never encounter a 2-second blank screen on navigation.
 */
export const DEFAULT_PLANS: CatalogPlan[] = [
  {
    id: "single",
    name: "Pay Per Template",
    price: 9,
    credits: 1,
    popular: false,
    per_template: 9.0,
    description: "One-time payment for single template generation",
    active: true,
  },
  {
    id: "plan_299",
    name: "Starter Pack",
    price: 299,
    credits: 51,
    popular: false,
    per_template: 5.86,
    description: "51 template credits — valid until consumed",
    active: true,
  },
  {
    id: "plan_499",
    name: "Professional Pack",
    price: 499,
    credits: 251,
    popular: true,
    per_template: 1.99,
    description: "251 template credits — most popular among advocates",
    active: true,
  },
  {
    id: "plan_999",
    name: "Premium Pack",
    price: 999,
    credits: 1111,
    popular: false,
    per_template: 0.9,
    description: "1,111 template credits — maximum value at ₹0.90/template",
    active: true,
  },
];

let inMemoryPlans: CatalogPlan[] = DEFAULT_PLANS;
let inMemoryWallet: { balance: number; total_used: number } | null = null;

export function getCachedPlans(): CatalogPlan[] {
  return inMemoryPlans;
}

export function setCachedPlans(plans: CatalogPlan[]): void {
  if (Array.isArray(plans) && plans.length > 0) {
    inMemoryPlans = plans;
  }
}

export function getCachedWallet(): { balance: number; total_used: number } | null {
  return inMemoryWallet;
}

export function setCachedWallet(w: { balance: number; total_used: number }): void {
  if (w && typeof w === "object") {
    inMemoryWallet = w;
  }
}
