import type { Restaurant } from "@/types/restaurant";
import generated from "./restaurants.json";

export const restaurants: Restaurant[] = generated as Restaurant[];
