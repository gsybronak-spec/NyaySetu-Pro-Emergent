/**
 * NyaySetu Pro - Frontend AI Intelligence Service.
 * Connects frontend drafting and workflow to backend AI endpoints.
 */

import { api } from "@/src/api/client";

export interface TemplateRecommendation {
  template_id: string;
  name: string;
  category: string;
  provision?: string;
  confidence: number;
  rationale: string;
  sample_grounds?: string[];
  alternatives?: { template_id: string; name: string }[];
}

export interface DraftingAssistance {
  template_id: string;
  provision: string;
  grounds: string[];
  prayer: string;
  legal_notice: string;
}

export interface CaseSummary {
  summary: string;
  case_number: string;
  court: string;
  status: string;
  parties: string;
}

export interface AIChatResponse {
  reply: string;
  disclaimer: string;
}

export const aiService = {
  /**
   * Suggest best template for a legal scenario or factual description.
   */
  async suggestTemplate(prompt: string, language: "gu" | "en" = "gu"): Promise<TemplateRecommendation> {
    try {
      const res = await api.aiSuggestTemplate(prompt, language);
      return res;
    } catch {
      return {
        template_id: "hazri_mafi",
        name: language === "gu" ? "હાજરી માફી અરજી" : "Haajari Mafi Application",
        category: "criminal",
        confidence: 0.5,
        rationale: "Default court template",
      };
    }
  },

  /**
   * Suggest drafting grounds, citations, and prayer clauses for a template.
   */
  async getDraftAssistance(templateId: string, caseFacts: string = "", language: "gu" | "en" = "gu"): Promise<DraftingAssistance> {
    try {
      const res = await api.aiDraftAssistance({ template_id: templateId, case_facts: caseFacts, language });
      return res;
    } catch {
      return {
        template_id: templateId,
        provision: "",
        grounds: [],
        prayer: "",
        legal_notice: "",
      };
    }
  },

  /**
   * Summarize a case or draft.
   */
  async summarizeCase(caseData: any, language: "gu" | "en" = "gu"): Promise<CaseSummary> {
    try {
      const res = await api.aiSummarize(JSON.stringify(caseData), language);
      return res;
    } catch {
      return {
        summary: caseData?.case_number ? `Case ${caseData.case_number}` : "Case summary unavailable",
        case_number: caseData?.case_number || "",
        court: caseData?.court || "",
        status: caseData?.status || "active",
        parties: `${caseData?.party_name || ""} vs ${caseData?.opposite_party || ""}`,
      };
    }
  },

  /**
   * Ask legal assistant for procedural advice or guidance.
   */
  async chat(message: string, history: any[] = [], context?: any): Promise<AIChatResponse> {
    try {
      const res = await api.aiChat(message, history, context);
      return res;
    } catch {
      return {
        reply: "AI Legal Assistant is temporarily unavailable. Please try again.",
        disclaimer: "Legal advice disclaimer.",
      };
    }
  },
};
