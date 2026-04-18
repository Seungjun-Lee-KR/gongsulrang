export type Restaurant = {
  rank: number;
  name: string;
  region: string;
  visits: number;
  totalAmount: number;
  avgAmount: number;
  deptCount: number;
  topAgency?: string;
  lat?: number;
  lng?: number;
};
