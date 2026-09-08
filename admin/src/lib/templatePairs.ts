export interface AdminTemplatePair {
  baseKey: string;
  guId: string;
  enId: string;
  name_gu: string;
  name_en: string;
  category: string;
}

export const ADMIN_TEMPLATE_PAIRS: AdminTemplatePair[] = [
  {
    baseKey: 'mudat_arji',
    guId: 'mudat_arji_gu',
    enId: 'mudat_arji_en',
    name_gu: 'મુદત અરજી',
    name_en: 'Adjournment Application (Time Petition)',
    category: 'General',
  },
  {
    baseKey: 'exemption_arji',
    guId: 'exemption_arji_gu',
    enId: 'exemption_arji_en',
    name_gu: 'હાજરી માફી અરજી',
    name_en: 'Exemption Application (Personal Appearance)',
    category: 'Criminal',
  },
  {
    baseKey: 'warrant_rad_karvani_arji',
    guId: 'warrant_rad_karvani_arji_gu',
    enId: 'warrant_rad_karvani_arji_en',
    name_gu: 'વોરંટ રદ કરવાની અરજી',
    name_en: 'Application for Cancellation / Recall of Warrant',
    category: 'Criminal',
  },
  {
    baseKey: 'vakilatnama_civil',
    guId: 'vakilatnama_civil_gu',
    enId: 'vakilatnama_civil_en',
    name_gu: 'વકીલાતનામું (દિવાની)',
    name_en: 'Vakalatnama (Civil)',
    category: 'Civil',
  },
  {
    baseKey: 'vakilatnama_criminal',
    guId: 'vakilatnama_criminal_gu',
    enId: 'vakilatnama_criminal_en',
    name_gu: 'વકીલાતનામું (ફોજદારી)',
    name_en: 'Vakalatnama (Criminal)',
    category: 'Criminal',
  },
  {
    baseKey: 'jamin_bond_swikarvani_arji',
    guId: 'jamin_bond_swikarvani_arji_gu',
    enId: 'jamin_bond_swikarvani_arji_en',
    name_gu: 'જામીન બોન્ડ રજૂ / સ્વીકારવાની અરજી',
    name_en: 'Application to Submit / Accept Bail Bond',
    category: 'Bail',
  },
  {
    baseKey: 'document_swikaravani_arji',
    guId: 'document_swikaravani_arji_gu',
    enId: 'document_swikaravani_arji_en',
    name_gu: 'દસ્તાવેજ રજૂ કરવા / સ્વીકારવાની અરજી',
    name_en: 'Application for Production and Acceptance of Documents',
    category: 'General',
  },
  {
    baseKey: 'document_parat_levani_arji',
    guId: 'document_parat_levani_arji_gu',
    enId: 'document_parat_levani_arji_en',
    name_gu: 'દસ્તાવેજ પરત મેળવવા બાબતની અરજી',
    name_en: 'Application for Return of Documents',
    category: 'General',
  },
  {
    baseKey: 'certified_report',
    guId: 'certified_report_gu',
    enId: 'certified_report_en',
    name_gu: 'સર્ટિફાઇડ રિપોર્ટ / નકલ મેળવવાની અરજી',
    name_en: 'Application for Certified Copy / Inspection Report',
    category: 'General',
  },
  {
    baseKey: 'samadhan_purshish',
    guId: 'samadhan_purshish_gu',
    enId: 'samadhan_purshish_en',
    name_gu: 'સમાધાન પુરશિસ',
    name_en: 'Compromise / Settlement Purshis',
    category: 'General',
  },
  {
    baseKey: 'aanke_padvani_arji',
    guId: 'aanke_padvani_arji_gu',
    enId: 'aanke_padvani_arji_en',
    name_gu: 'આંક પાડવાની અરજી',
    name_en: 'Application to Exhibit Document',
    category: 'General',
  },
  {
    baseKey: 'closing_purshish',
    guId: 'closing_purshish_gu',
    enId: 'closing_purshish_en',
    name_gu: 'પુરાવો બંધ પુરશિસ',
    name_en: 'Closing Purshis (Closure of Evidence)',
    category: 'General',
  },
  {
    baseKey: 'saaxi_ne_summons',
    guId: 'saaxi_ne_summons_gu',
    enId: 'saaxi_ne_summons_en',
    name_gu: 'સાક્ષીને સમન્સ કાઢવાની અરજી',
    name_en: 'Application to Issue Witness Summons',
    category: 'General',
  },
  {
    baseKey: 'kam_board_par_levani_arji',
    guId: 'kam_board_par_levani_arji_gu',
    enId: 'kam_board_par_levani_arji_en',
    name_gu: 'કામ બોર્ડ પર લેવાની અરજી',
    name_en: 'Application to Take Matter on Board (Early Hearing)',
    category: 'General',
  },
  {
    baseKey: 'dd_karavani_arji',
    guId: 'dd_karavani_arji_gu',
    enId: 'dd_karavani_arji_en',
    name_gu: 'ડી.ડી. કરાવવા અંગેની અરજી (ડિસમિસ ઇન ડિફોલ્ટ)',
    name_en: 'Application for Dismissal in Default (D.D.)',
    category: 'Civil',
  },
  {
    baseKey: 'warrant_no_hath_bido_apvani_arji',
    guId: 'warrant_no_hath_bido_apvani_arji_gu',
    enId: 'warrant_no_hath_bido_apvani_arji_en',
    name_gu: 'વોરંટ / સમન્સનો હાથબીડો આપવાની અરજી',
    name_en: 'Application for Direct Service / Hand Delivery of Warrant or Summons',
    category: 'Criminal',
  },
  {
    baseKey: 'undertaking',
    guId: 'undertaking_gu',
    enId: 'undertaking_en',
    name_gu: 'બાંહેધરી પત્રક (અન્ડરટેકિંગ)',
    name_en: 'Undertaking / Bond',
    category: 'General',
  },
  {
    baseKey: 'ulat_tapas_no_haq_bandh_karavani_arji',
    guId: 'ulat_tapas_no_haq_bandh_karavani_arji_gu',
    enId: 'ulat_tapas_no_haq_bandh_karavani_arji_en',
    name_gu: 'ઉલટ તપાસનો હક બંધ કરવાની અરજી',
    name_en: 'Application to Close the Right of Cross-Examination',
    category: 'General',
  },
  {
    baseKey: 'ulat_tapas_no_haq_kholvani_arji',
    guId: 'ulat_tapas_no_haq_kholvani_arji_gu',
    enId: 'ulat_tapas_no_haq_kholvani_arji_en',
    name_gu: 'ઉલટ તપાસનો હક ખોલવાની અરજી',
    name_en: 'Application to Reopen / Recall Right of Cross-Examination',
    category: 'General',
  },
  {
    baseKey: 'fs_no_haq_bandh_karvani_arji',
    guId: 'fs_no_haq_bandh_karvani_arji_gu',
    enId: 'fs_no_haq_bandh_karvani_arji_en',
    name_gu: 'ફર્ધર સ્ટેટમેન્ટ (F.S.) હક બંધ કરવાની અરજી',
    name_en: 'Application to Close the Right of Further Statement (F.S.)',
    category: 'Criminal',
  },
  {
    baseKey: 'fs_no_haq_kholvani_arji',
    guId: 'fs_no_haq_kholvani_arji_gu',
    enId: 'fs_no_haq_kholvani_arji_en',
    name_gu: 'ફર્ધર સ્ટેટમેન્ટ (F.S.) હક ખોલવાની અરજી',
    name_en: 'Application to Reopen Right of Further Statement (F.S.)',
    category: 'Criminal',
  },
];

export function getOrderedAdminPairs(order?: string[] | null): AdminTemplatePair[] {
  if (!Array.isArray(order) || order.length === 0) {
    return [...ADMIN_TEMPLATE_PAIRS];
  }
  const orderMap = new Map<string, number>();
  order.forEach((key, index) => {
    if (typeof key === 'string' && key.trim()) {
      const k = key.trim();
      const base = k.replace(/_(gu|en)$/, '');
      orderMap.set(k, index);
      orderMap.set(base, index);
    }
  });

  return [...ADMIN_TEMPLATE_PAIRS].sort((a, b) => {
    const idxA = orderMap.has(a.baseKey) ? orderMap.get(a.baseKey)! : 9999;
    const idxB = orderMap.has(b.baseKey) ? orderMap.get(b.baseKey)! : 9999;
    return idxA - idxB;
  });
}
