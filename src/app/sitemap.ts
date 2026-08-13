import type { MetadataRoute } from "next";
import { restaurants } from "@/data/restaurants";
import { districtMomentum } from "@/data/momentum-districts";
import {
  getAgencySummaries,
  getRegionSummaries,
  slugifyAgency,
} from "@/lib/aggregations";

const BASE = "https://gongsulrang.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  const staticEntries: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE}/trending`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE}/region`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE}/agency`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${BASE}/map`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
  ];

  const trendingEntries: MetadataRoute.Sitemap = districtMomentum.map((d) => ({
    url: `${BASE}/trending/${encodeURIComponent(d.name)}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  const regionEntries: MetadataRoute.Sitemap = getRegionSummaries().map((s) => ({
    url: `${BASE}/region/${encodeURIComponent(s.region)}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  const agencyEntries: MetadataRoute.Sitemap = getAgencySummaries().map((s) => ({
    url: `${BASE}/agency/${slugifyAgency(s.agency)}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.6,
  }));

  const restaurantEntries: MetadataRoute.Sitemap = restaurants.map((r) => ({
    url: `${BASE}/restaurant/${r.rank}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.5,
  }));

  return [
    ...staticEntries,
    ...trendingEntries,
    ...regionEntries,
    ...agencyEntries,
    ...restaurantEntries,
  ];
}
