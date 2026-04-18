import type { Restaurant } from "@/types/restaurant";
import generated from "./restaurants.json";
import { sampleRestaurants } from "./sample-restaurants";

const loaded = generated as Restaurant[];

export const restaurants: Restaurant[] =
  loaded.length > 0 ? loaded : sampleRestaurants;

export const usingSampleData = loaded.length === 0;
