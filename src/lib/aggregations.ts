import type { Restaurant } from "@/types/restaurant";
import { restaurants } from "@/data/restaurants";

export type RegionSummary = {
  region: string;
  restaurantCount: number;
  totalVisits: number;
  totalAmount: number;
  topRestaurant: Restaurant;
};

export type AgencySummary = {
  agency: string;
  restaurantCount: number;
  totalVisits: number;
  totalAmount: number;
  topRestaurant: Restaurant;
};

export function getRegionSummaries(): RegionSummary[] {
  const groups = new Map<string, Restaurant[]>();
  for (const r of restaurants) {
    const key = r.region || "기타";
    const arr = groups.get(key) ?? [];
    arr.push(r);
    groups.set(key, arr);
  }
  const out: RegionSummary[] = [];
  for (const [region, list] of groups) {
    list.sort((a, b) => b.visits - a.visits);
    out.push({
      region,
      restaurantCount: list.length,
      totalVisits: list.reduce((s, r) => s + r.visits, 0),
      totalAmount: list.reduce((s, r) => s + r.totalAmount, 0),
      topRestaurant: list[0],
    });
  }
  out.sort((a, b) => b.totalVisits - a.totalVisits);
  return out;
}

export function getRestaurantsByRegion(region: string): Restaurant[] {
  return restaurants
    .filter((r) => r.region === region)
    .sort((a, b) => b.visits - a.visits);
}

export function getAgencySummaries(): AgencySummary[] {
  const groups = new Map<string, Restaurant[]>();
  for (const r of restaurants) {
    if (!r.topAgency) continue;
    const key = r.topAgency;
    const arr = groups.get(key) ?? [];
    arr.push(r);
    groups.set(key, arr);
  }
  const out: AgencySummary[] = [];
  for (const [agency, list] of groups) {
    list.sort((a, b) => b.visits - a.visits);
    out.push({
      agency,
      restaurantCount: list.length,
      totalVisits: list.reduce((s, r) => s + r.visits, 0),
      totalAmount: list.reduce((s, r) => s + r.totalAmount, 0),
      topRestaurant: list[0],
    });
  }
  out.sort((a, b) => b.totalVisits - a.totalVisits);
  return out;
}

export function getRestaurantsByAgency(agency: string): Restaurant[] {
  return restaurants
    .filter((r) => r.topAgency === agency)
    .sort((a, b) => b.visits - a.visits);
}

export function slugifyAgency(agency: string): string {
  return encodeURIComponent(agency);
}

export function unslugifyAgency(slug: string): string {
  return decodeURIComponent(slug);
}
