import type { DistrictMomentum, DistrictMomentumFile } from "@/types/momentum";
import generated from "./momentum-districts.json";

// scripts/15_momentum_districts.py가 생성 (13의 랭킹 + 구 중심 카카오 매칭)
export const districtMomentum: DistrictMomentum[] = (
  generated as DistrictMomentumFile
).districts;

export function getDistrictMomentum(name: string): DistrictMomentum | undefined {
  return districtMomentum.find((d) => d.name === name);
}
