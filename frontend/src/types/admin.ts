/**
 * TypeScript definitions for NyaySetu Pro Super Admin Portal (Phase 3)
 */

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: "super_admin" | "staff_admin" | "admin";
  active: boolean;
  last_login?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AdminDashboardStats {
  total_users: number;
  recent_users_30d: number;
  total_cases: number;
  total_documents_generated: number;
  total_credits_consumed: number;
  total_transactions: number;
  recent_users: {
    id: string;
    name?: string;
    mobile?: string;
    email?: string;
    provider?: string;
    created_at?: string;
  }[];
  recent_applications: {
    id: string;
    user_id?: string;
    template_name?: string;
    language?: string;
    format?: string;
    created_at?: string;
  }[];
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  limit?: number;
  offset?: number;
  total_pages: number;
  [key: string]: any;
}

export interface LawyerUser {
  id: string;
  name?: string;
  first_name?: string;
  middle_name?: string;
  last_name?: string;
  email?: string;
  mobile?: string;
  provider?: string;
  role?: string;
  user_type?: string;
  bar_council_no?: string;
  advocate_name_en?: string;
  advocate_name_gu?: string;
  state?: string;
  district?: string;
  taluka?: string;
  court?: string;
  active: boolean;
  status: "active" | "suspended" | "banned";
  is_profile_complete?: boolean;
  profile_completed?: boolean;
  created_at: string;
  updated_at?: string;
  last_active?: string;
  wallet_balance?: number;
  wallet?: {
    balance: number;
    free_credits_granted?: number;
    total_used?: number;
  };
}

export interface UserDetailResponse {
  user: LawyerUser;
  wallet: {
    user_id: string;
    balance: number;
    free_credits_granted: number;
    total_used: number;
    total_purchased?: number;
    created_at?: string;
    updated_at?: string;
  };
  cases_count: number;
  applications_count: number;
  recent_transactions: TransactionItem[];
}

export interface TransactionItem {
  id: string;
  user_id: string;
  type: "credit" | "debit" | "purchase" | "admin_adjustment" | "refund" | "referral_bonus";
  amount?: number;
  credits: number;
  balance_before?: number;
  balance_after?: number;
  reason?: string;
  reference?: string;
  status: "success" | "pending" | "failed";
  admin_id?: string;
  admin_email?: string;
  created_at: string;
}

export interface AdminCaseItem {
  id: string;
  user_id: string;
  nickname?: string;
  case_number?: string;
  party_name?: string;
  party_role?: string;
  opposite_party?: string;
  opposite_party_role?: string;
  court?: string;
  court_id?: string;
  court_label?: string;
  district_id?: string;
  district_label?: string;
  taluka_id?: string;
  taluka_label?: string;
  case_type_id?: string;
  case_type_label?: string;
  category?: string;
  status: "active" | "archived" | "closed";
  created_at: string;
  updated_at?: string;
  owner?: {
    id: string;
    name?: string;
    mobile?: string;
    email?: string;
    provider?: string;
    active?: boolean;
  };
}

export interface CaseDetailResponse {
  case: AdminCaseItem;
  owner: LawyerUser | null;
  applications: AdminApplicationItem[];
  drafts: any[];
}

export interface AdminApplicationItem {
  id: string;
  user_id: string;
  case_id?: string;
  template_id?: string;
  template_name?: string;
  template_name_gu?: string;
  template_version?: number;
  language: "gu" | "en";
  format: "pdf" | "docx" | "odt" | "png";
  filename: string;
  file_size?: number;
  sha256?: string;
  engine?: string;
  font_family?: string;
  generator_version?: string;
  created_at: string;
}

export interface ApplicationDetailResponse {
  application: AdminApplicationItem;
  owner?: LawyerUser | null;
  case?: AdminCaseItem | null;
  draft?: any | null;
}

export interface AdminTemplateItem {
  id: string;
  slug?: string;
  name_en: string;
  name_gu: string;
  category: string;
  sub_category?: string;
  description?: string;
  tags?: string[];
  aliases?: string[];
  case_types?: string[];
  courts?: string[];
  jurisdiction?: string;
  version: number;
  status: "published" | "draft" | "archived";
  source: "seed" | "admin_edited" | "custom";
  locked: boolean;
  revision_count: number;
  is_seed_template?: boolean;
  fields?: TemplateField[];
  placeholders?: string[];
  content_en?: string;
  content_gu?: string;
  editor_content_gu?: Record<string, any> | null;
  editor_content_en?: Record<string, any> | null;
  settings?: {
    margin_top_cm?: number;
    margin_bottom_cm?: number;
    margin_left_cm?: number;
    margin_right_cm?: number;
    gujarati_font?: string;
    english_font?: string;
    body_size?: number;
    heading_size?: number;
    page_size?: string;
    [key: string]: any;
  };
  created_by?: string;
  updated_by?: string;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
}

export interface TemplateField {
  key: string;
  label_en: string;
  label_gu: string;
  type: "text" | "number" | "date" | "select" | "radio" | "checkbox" | "textarea";
  required?: boolean;
  default_value?: any;
  options?: { value: string; label_en: string; label_gu: string }[];
  order?: number;
  [key: string]: any;
}

export interface AdminTemplateRevision {
  id: string;
  template_id: string;
  version: number;
  title: string;
  name_en: string;
  name_gu: string;
  category: string;
  sub_category?: string;
  description?: string;
  fields: TemplateField[];
  placeholders: string[];
  content_en: string;
  content_gu: string;
  editor_content_gu?: Record<string, any> | null;
  editor_content_en?: Record<string, any> | null;
  settings?: Record<string, any>;
  metadata?: {
    source?: string;
    status?: string;
    [key: string]: any;
  };
  created_by?: string;
  published_at?: string | null;
  created_at: string;
}

export interface CatalogItem {
  id: string;
  name_en?: string;
  name_gu?: string;
  name?: string;
  en?: string;
  gu?: string;
  active?: boolean;
  district_id?: string;
  cat?: string;
  sections?: { id: string; label: string; bailable?: boolean }[];
  created_at?: string;
  updated_at?: string;
  [key: string]: any;
}

export type CatalogKind = "courts" | "districts" | "talukas" | "laws" | "police-stations" | "case-types";

export interface AdminPlanItem {
  id: string;
  name: string;
  credits: number;
  price: number;
  original_price?: number;
  discount_pct?: number;
  popular?: boolean;
  active: boolean;
  description?: string;
  features?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface AdminAuditLogItem {
  id: string;
  admin_id?: string;
  admin_name?: string;
  admin_email?: string;
  admin_role?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  target?: string;
  old_value?: any;
  new_value?: any;
  reason?: string;
  metadata?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  timestamp?: string;
}
