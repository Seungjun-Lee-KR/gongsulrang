#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import Papa from "papaparse";

const args = process.argv.slice(2);
if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
  console.log(
    "Usage: node scripts/load-data.mjs <공슐랭_랭킹.csv> [--limit N]\n" +
      "  공슐랭 랭킹 CSV(지방재정365 수집기 출력)를 src/data/restaurants.json으로 변환합니다.",
  );
  process.exit(args.length === 0 ? 1 : 0);
}

const csvPath = resolve(args[0]);
const limitIdx = args.indexOf("--limit");
const limit = limitIdx >= 0 ? parseInt(args[limitIdx + 1] ?? "", 10) : undefined;

const text = readFileSync(csvPath, "utf8");
const parsed = Papa.parse(text, {
  header: true,
  skipEmptyLines: true,
  transformHeader: (h) => h.replace(/^\ufeff/, "").trim(),
});

if (parsed.errors.length > 0) {
  console.warn(`⚠️  파싱 경고 ${parsed.errors.length}건 (처음 3건):`);
  for (const e of parsed.errors.slice(0, 3)) console.warn("   ", e);
}

const REQUIRED = [
  "식당명",
  "지역",
  "이용횟수",
  "총이용금액",
  "평균금액",
  "집행부서수",
  "순위",
];
const fields = parsed.meta.fields ?? [];
const missing = REQUIRED.filter((c) => !fields.includes(c));
if (missing.length) {
  console.error(`❌ 필수 컬럼 누락: ${missing.join(", ")}`);
  console.error(`   발견된 컬럼: ${fields.join(", ")}`);
  process.exit(1);
}

const toNum = (v) => {
  const n = Number(String(v ?? "").replace(/,/g, ""));
  return Number.isFinite(n) ? n : NaN;
};

let restaurants = parsed.data
  .map((row) => ({
    rank: toNum(row["순위"]),
    name: String(row["식당명"] ?? "").trim(),
    region: String(row["지역"] ?? "").trim(),
    visits: toNum(row["이용횟수"]),
    totalAmount: toNum(row["총이용금액"]),
    avgAmount: toNum(row["평균금액"]),
    deptCount: toNum(row["집행부서수"]),
  }))
  .filter(
    (r) =>
      r.name &&
      Number.isFinite(r.rank) &&
      Number.isFinite(r.visits) &&
      Number.isFinite(r.totalAmount),
  )
  .sort((a, b) => a.rank - b.rank);

if (limit && limit > 0) restaurants = restaurants.slice(0, limit);

const outPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../src/data/restaurants.json",
);
writeFileSync(outPath, JSON.stringify(restaurants, null, 2) + "\n", "utf8");

console.log(`✅ ${restaurants.length}건 로드 완료 → ${outPath}`);
if (restaurants.length > 0) {
  const top = restaurants[0];
  console.log(`   1위: ${top.name} (${top.region}) — ${top.visits.toLocaleString()}회`);
}
