export type Restaurant = {
  rank: number;
  /** 실제 간판 상호 (scripts/16이 카카오로 보정). 미보정 시 장부명 그대로 */
  name: string;
  /** 보정 전 카드 명세서상 상호 (name과 다를 때만 존재) */
  ledgerName?: string;
  region: string;
  visits: number;
  totalAmount: number;
  avgAmount: number;
  deptCount: number;
  topAgency?: string;
  lat?: number;
  lng?: number;
  placeId?: string;
  rating?: number;
  ratingCount?: number;
  phone?: string;
  hours?: string[];
  photos?: string[];
  googleMapsUri?: string;
  formattedAddress?: string;
  address?: string;
  guDong?: string;
};
