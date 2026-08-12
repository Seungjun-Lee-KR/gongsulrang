import type { MomentumData } from "@/types/momentum";
import generated from "./momentum.json";

// scripts/14_kakao_place_match.py가 생성 (scripts/13이 랭킹, 14가 카카오 앵커링)
export const momentum: MomentumData = generated as MomentumData;
